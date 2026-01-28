# ACTION_TEST_MATRIX - Microaction Test Specifications

**Generated:** 2026-01-13
**Source:** COMPLETE_ACTION_EXECUTION_CATALOG.md (6584 lines)
**Purpose:** Actionable test cases for 67 microactions

---

## Test Case Format

Each action has:
- **API Request:** Exact payload
- **Expected DB Diff:** Tables + columns changed
- **Expected Audit Row:** audit_log entry
- **Expected UI State:** Frontend response

---

## CLUSTER 01: FIX_SOMETHING (7 actions)

### 1.1 diagnose_fault

**Classification:** MUTATE_MEDIUM
**Tables:** `pms_faults`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "diagnose_fault",
  "context": {
    "fault_id": "<uuid>",
    "diagnosis_text": "Thermostat stuck open",
    "root_cause": "Component aging",
    "next_action": "create_work_order"
  }
}
```

**Expected DB Diff:**
```sql
-- pms_faults
UPDATE pms_faults SET
  status = 'diagnosed',
  diagnosis_text = 'Thermostat stuck open',
  root_cause = 'Component aging',
  diagnosed_by = <user_id>,
  diagnosed_at = NOW()
WHERE id = <fault_id>;
```

**Expected Audit Row:**
```json
{
  "action": "diagnose_fault",
  "entity_type": "fault",
  "entity_id": "<fault_id>",
  "changes_summary": "Diagnosed fault: ..."
}
```

**Assertions:**
- [ ] Fault status changed to 'diagnosed'
- [ ] diagnosis_text populated
- [ ] audit_log row created

---

### 1.2 show_manual_section

**Classification:** READ
**Tables:** None (query only)

**API Request:**
```json
POST /search
{
  "query": "MTU-OVHT-01 troubleshooting",
  "limit": 5
}
```

**Expected Response:**
```json
{
  "success": true,
  "results": [
    {
      "type": "document_chunk",
      "content": "High Coolant Temperature...",
      "page_number": 142
    }
  ]
}
```

**Assertions:**
- [ ] Returns document chunks
- [ ] Results include manual content
- [ ] No DB mutations

---

## CLUSTER 02: DO_MAINTENANCE (16 actions)

### 2.1 create_work_order

**Classification:** MUTATE_MEDIUM
**Tables:** `pms_work_orders`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "create_work_order",
  "context": {
    "title": "Starboard Thruster Inspection",
    "work_type": "preventive",
    "equipment_id": "<uuid>",
    "priority": "normal",
    "due_date": "2026-01-20",
    "description": "Routine inspection per schedule"
  }
}
```

**Expected DB Diff:**
```sql
INSERT INTO pms_work_orders (
  yacht_id, number, title, work_type, equipment_id,
  priority, due_date, description, status, created_by
) VALUES (
  'TEST_YACHT_001', 'WO-2026-XXX', 'Starboard Thruster Inspection',
  'preventive', '<uuid>', 'normal', '2026-01-20',
  'Routine inspection per schedule', 'candidate', <user_id>
);
```

**Expected Audit Row:**
```json
{
  "action": "create_work_order",
  "entity_type": "work_order",
  "new_values": {
    "title": "Starboard Thruster Inspection",
    "work_type": "preventive"
  }
}
```

**Assertions:**
- [ ] Work order created with status 'candidate'
- [ ] WO number generated (format: WO-YYYY-NNN)
- [ ] audit_log row created

---

### 2.2 mark_work_order_complete

**Classification:** MUTATE_MEDIUM
**Tables:** `pms_work_orders`, `audit_log`

**Precondition:** Work order exists with status 'in_progress'

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "mark_work_order_complete",
  "context": {
    "work_order_id": "<uuid>",
    "completion_notes": "All items checked, no issues found"
  }
}
```

**Expected DB Diff:**
```sql
UPDATE pms_work_orders SET
  status = 'completed',
  completed_at = NOW(),
  completed_by = <user_id>
WHERE id = <work_order_id>;
```

**Assertions:**
- [ ] Status changed to 'completed'
- [ ] completed_at timestamp set
- [ ] audit_log row with old/new status

---

### 2.3 add_note_to_work_order

**Classification:** MUTATE_LOW
**Tables:** `work_order_notes` or `pms_work_orders.notes`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "add_note_to_work_order",
  "context": {
    "work_order_id": "<uuid>",
    "note_text": "Ordered replacement part, ETA 3 days"
  }
}
```

**Assertions:**
- [ ] Note added to work order
- [ ] audit_log row created
- [ ] Note includes timestamp and author

---

### 2.4 add_part_to_work_order

**Classification:** MUTATE_LOW
**Tables:** `work_order_parts`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "add_part_to_work_order",
  "context": {
    "work_order_id": "<uuid>",
    "part_id": "<uuid>",
    "quantity": 2
  }
}
```

**Assertions:**
- [ ] Part linked to work order
- [ ] Quantity recorded
- [ ] audit_log row created

---

## CLUSTER 03: MANAGE_EQUIPMENT (6 actions)

### 3.1 show_equipment_overview

**Classification:** READ

**API Request:**
```json
POST /search
{
  "query": "generator 2 overview",
  "limit": 1
}
```

**Assertions:**
- [ ] Returns equipment card
- [ ] Includes: name, status, criticality, location
- [ ] No DB mutations

---

### 3.2 update_equipment_status

**Classification:** MUTATE_LOW
**Tables:** `pms_equipment`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "update_equipment_status",
  "context": {
    "equipment_id": "<uuid>",
    "new_status": "degraded",
    "reason": "Abnormal vibration detected"
  }
}
```

**Expected DB Diff:**
```sql
UPDATE pms_equipment SET
  status = 'degraded',
  updated_at = NOW()
WHERE id = <equipment_id>;
```

**Assertions:**
- [ ] Status changed to 'degraded'
- [ ] audit_log records old and new status

---

## CLUSTER 04: INVENTORY & PARTS (7 actions)

### 4.1 check_stock_level

**Classification:** READ

**API Request:**
```json
POST /search
{
  "query": "oil filter stock level",
  "limit": 5
}
```

**Assertions:**
- [ ] Returns inventory items
- [ ] Includes: quantity_on_hand, minimum_quantity
- [ ] Shows low stock warnings

---

### 4.2 log_part_usage

**Classification:** MUTATE_LOW
**Tables:** `parts_inventory`, `parts_usage_log`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "log_part_usage",
  "context": {
    "part_id": "<uuid>",
    "quantity_used": 1,
    "work_order_id": "<uuid>",
    "equipment_id": "<uuid>"
  }
}
```

**Expected DB Diff:**
```sql
-- Decrement inventory
UPDATE parts_inventory SET
  quantity_on_hand = quantity_on_hand - 1
WHERE id = <part_id>;

-- Log usage
INSERT INTO parts_usage_log (...) VALUES (...);
```

**Assertions:**
- [ ] quantity_on_hand decremented
- [ ] Usage logged with work_order link
- [ ] audit_log row created

---

## CLUSTER 05: HANDOVER & COMMUNICATION (9 actions)

### 5.1 add_to_handover

**Classification:** MUTATE_LOW
**Tables:** `handover_items`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "add_to_handover",
  "context": {
    "title": "Generator 2 vibration issue",
    "description": "Monitor closely, may need overhaul",
    "category": "equipment",
    "priority": "high",
    "entity_type": "fault",
    "entity_id": "<uuid>"
  }
}
```

**Expected DB Diff:**
```sql
INSERT INTO handover_items (
  yacht_id, title, description, category, priority,
  entity_type, entity_id, status, created_by
) VALUES (...);
```

**Assertions:**
- [ ] Handover item created
- [ ] Linked to source entity
- [ ] audit_log row created

---

## CLUSTER 06: COMPLIANCE & HOURS OF REST (5 actions)

### 6.1 update_hours_of_rest

**Classification:** MUTATE_LOW
**Tables:** `hours_of_rest`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "update_hours_of_rest",
  "context": {
    "date": "2026-01-13",
    "rest_periods": [
      {"start": "00:00", "end": "06:00"},
      {"start": "22:00", "end": "24:00"}
    ]
  }
}
```

**Assertions:**
- [ ] HOR record created/updated
- [ ] Validates MLC compliance (10hr minimum)
- [ ] audit_log row created

---

## CLUSTER 07: DOCUMENTS (22 actions)

### 7.1 open_document

**Classification:** READ

**API Request:**
```json
POST /v1/documents/<doc_id>/sign
Authorization: Bearer <jwt>
```

**Assertions:**
- [ ] Returns signed URL
- [ ] URL has 10-minute TTL
- [ ] audit_log records access

---

### 7.2 search_documents

**Classification:** READ

**API Request:**
```json
POST /search
{
  "query": "engine overhaul procedure",
  "limit": 10
}
```

**Assertions:**
- [ ] Returns document chunks
- [ ] Includes page numbers
- [ ] Ranked by relevance

---

## CLUSTER 08: PURCHASING (7 actions)

### 8.1 create_purchase_request

**Classification:** MUTATE_MEDIUM
**Tables:** `purchase_requests`, `shopping_list_items`, `audit_log`

**API Request:**
```json
POST /v1/actions/execute
{
  "action_name": "create_purchase_request",
  "context": {
    "part_id": "<uuid>",
    "quantity": 5,
    "urgency": "normal",
    "notes": "Restock before next voyage"
  }
}
```

**Assertions:**
- [ ] Purchase request created
- [ ] Shopping list item added
- [ ] audit_log row created

---

## Summary: Test Coverage Requirements

| Cluster | Actions | Minimum Tests |
|---------|---------|---------------|
| 01 FIX_SOMETHING | 7 | 3 |
| 02 DO_MAINTENANCE | 16 | 5 |
| 03 MANAGE_EQUIPMENT | 6 | 2 |
| 04 INVENTORY | 7 | 2 |
| 05 HANDOVER | 9 | 2 |
| 06 COMPLIANCE | 5 | 1 |
| 07 DOCUMENTS | 22 | 3 |
| 08 PURCHASING | 7 | 2 |
| **TOTAL** | **67** | **20** |

---

## Evidence Requirements Per Test

For each test, capture:
1. **Request:** Full HTTP request with headers
2. **Response:** HTTP status + body
3. **DB Before:** Relevant rows before action
4. **DB After:** Relevant rows after action
5. **Audit Log:** New audit_log row

---

**Last Updated:** 2026-01-13
