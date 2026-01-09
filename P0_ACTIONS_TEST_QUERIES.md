# P0 Actions Test Queries & Scenarios

**Date:** 2026-01-09
**Purpose:** Complete test scenarios with sample queries to validate all P0 actions and situation triggers
**Database:** Supabase PostgreSQL

---

## 📋 Table of Contents

1. [Database Setup Queries](#database-setup-queries)
2. [Test Data Creation](#test-data-creation)
3. [P0 Action Test Scenarios](#p0-action-test-scenarios)
4. [Situation Triggers](#situation-triggers)
5. [Audit Trail Verification](#audit-trail-verification)
6. [Edge Cases](#edge-cases)

---

## Database Setup Queries

### Check Migration Status

```sql
-- Check if accountability columns exist on pms_parts
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pms_parts'
  AND column_name IN ('quantity_on_hand', 'minimum_quantity', 'unit', 'location', 'last_counted_at', 'last_counted_by');

-- Expected: 6 rows returned
```

```sql
-- Check if accountability columns exist on pms_work_orders
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pms_work_orders'
  AND column_name IN ('fault_id', 'assigned_to', 'completed_by', 'completed_at', 'completion_notes');

-- Expected: 5 rows returned
```

```sql
-- Check if new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('pms_audit_log', 'pms_part_usage', 'pms_work_order_notes', 'pms_handover');

-- Expected: 4 rows returned
```

---

## Test Data Creation

### 1. Get Existing Data IDs

```sql
-- Get a yacht ID for testing
SELECT id, name
FROM yachts
LIMIT 1;

-- Save this as: TEST_YACHT_ID
```

```sql
-- Get a user ID for testing
SELECT id, email, full_name
FROM user_profiles
WHERE yacht_id = 'TEST_YACHT_ID'
LIMIT 1;

-- Save this as: TEST_USER_ID
```

```sql
-- Get equipment with faults
SELECT
  e.id as equipment_id,
  e.name as equipment_name,
  e.location,
  f.id as fault_id,
  f.fault_code,
  f.title as fault_title,
  f.severity
FROM pms_equipment e
INNER JOIN pms_faults f ON f.equipment_id = e.id
WHERE e.yacht_id = 'TEST_YACHT_ID'
  AND f.status = 'open'
LIMIT 5;

-- Save IDs for testing:
-- TEST_EQUIPMENT_ID
-- TEST_FAULT_ID
```

```sql
-- Get parts with inventory
SELECT
  id,
  name,
  part_number,
  quantity_on_hand,
  minimum_quantity,
  unit,
  location
FROM pms_parts
WHERE yacht_id = 'TEST_YACHT_ID'
  AND quantity_on_hand > 5
LIMIT 5;

-- Save this as: TEST_PART_ID (one with good stock)
-- TEST_PART_ID_LOW (one with low stock)
```

```sql
-- Get a work order for testing
SELECT
  id,
  number,
  title,
  status,
  equipment_id,
  fault_id
FROM pms_work_orders
WHERE yacht_id = 'TEST_YACHT_ID'
  AND status = 'in_progress'
LIMIT 1;

-- Save this as: TEST_WO_ID
```

### 2. Create Test Data (If Needed)

```sql
-- Create test equipment if none exists
INSERT INTO pms_equipment (
  id,
  yacht_id,
  name,
  equipment_type,
  manufacturer,
  model,
  location,
  status
) VALUES (
  gen_random_uuid(),
  'TEST_YACHT_ID',
  'Test Generator',
  'generator',
  'Caterpillar',
  'C18',
  'Engine Room',
  'operational'
) RETURNING id;

-- Save as: TEST_EQUIPMENT_ID
```

```sql
-- Create test fault
INSERT INTO pms_faults (
  id,
  yacht_id,
  equipment_id,
  fault_code,
  title,
  description,
  severity,
  status,
  reported_by,
  reported_at
) VALUES (
  gen_random_uuid(),
  'TEST_YACHT_ID',
  'TEST_EQUIPMENT_ID',
  'E001',
  'High Temperature Alarm',
  'Generator coolant temperature exceeds normal operating range. Needs immediate investigation.',
  'high',
  'open',
  'TEST_USER_ID',
  NOW()
) RETURNING id;

-- Save as: TEST_FAULT_ID
```

```sql
-- Create test part
INSERT INTO pms_parts (
  id,
  yacht_id,
  name,
  part_number,
  category,
  quantity_on_hand,
  minimum_quantity,
  unit,
  location
) VALUES (
  gen_random_uuid(),
  'TEST_YACHT_ID',
  'Oil Filter',
  'OF-12345',
  'filters',
  15,
  5,
  'pieces',
  'Engine Room - Shelf A2'
) RETURNING id;

-- Save as: TEST_PART_ID
```

---

## P0 Action Test Scenarios

### Test 1: show_manual_section (P0 Action #1 - READ)

**Purpose:** Display equipment manual sections
**API Endpoint:** `POST /v1/actions/execute` (action: show_manual_section)

**Pre-Query Check:**
```sql
-- Check if equipment has manual chunks
SELECT
  dc.id,
  dc.document_id,
  dc.text,
  dc.page_number,
  d.title,
  d.manufacturer,
  d.model
FROM document_chunks dc
INNER JOIN documents d ON d.id = dc.document_id
WHERE d.equipment_type = (
  SELECT equipment_type
  FROM pms_equipment
  WHERE id = 'TEST_EQUIPMENT_ID'
)
LIMIT 5;

-- Expected: Manual sections related to equipment type
```

**Test Query:**
```bash
# API Call
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "show_manual_section",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "equipment_id": "TEST_EQUIPMENT_ID",
      "fault_code": "E001"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Response includes manual sections
- Signed PDF URL returned
- No database mutations

**Verification Query:**
```sql
-- Should be NO new entries (READ action)
SELECT COUNT(*) FROM pms_audit_log WHERE action = 'show_manual_section';
-- Expected: 0 (READ actions don't create audit logs)
```

---

### Test 2: check_stock_level (P0 Action #6 - READ)

**Purpose:** Check part inventory level with analytics
**API Endpoint:** `POST /v1/actions/execute` (action: check_stock_level)

**Pre-Query Check:**
```sql
-- Check current stock level
SELECT
  name,
  part_number,
  quantity_on_hand,
  minimum_quantity,
  unit,
  location,
  last_counted_at,
  last_counted_by
FROM pms_parts
WHERE id = 'TEST_PART_ID';

-- Expected: Part details with current stock
```

**Test Query:**
```bash
# API Call
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "check_stock_level",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "part_id": "TEST_PART_ID"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Current stock matches database
- Stock status calculated (low/adequate/excess)
- Usage analytics for last 30 days
- No database mutations

**Verification Query:**
```sql
-- Check 30-day usage analytics
SELECT
  COUNT(*) as usage_count,
  SUM(quantity) as total_used,
  AVG(quantity) as avg_per_use
FROM pms_part_usage
WHERE part_id = 'TEST_PART_ID'
  AND used_at >= NOW() - INTERVAL '30 days';

-- Expected: Usage statistics
```

---

### Test 3: create_work_order_from_fault (P0 Action #2 - MUTATE + Signature)

**Purpose:** Create work order from an open fault
**API Endpoints:**
- `GET /v1/actions/create_work_order_from_fault/prefill?fault_id=...`
- `POST /v1/actions/create_work_order_from_fault/preview`
- `POST /v1/actions/execute` (action: create_work_order_from_fault)

#### Step 1: Prefill

**Pre-Query Check:**
```sql
-- Check fault status and existing WO
SELECT
  f.id,
  f.fault_code,
  f.title,
  f.severity,
  e.name as equipment_name,
  e.location,
  wo.id as existing_wo_id,
  wo.number as existing_wo_number
FROM pms_faults f
INNER JOIN pms_equipment e ON e.id = f.equipment_id
LEFT JOIN pms_work_orders wo ON wo.fault_id = f.id
WHERE f.id = 'TEST_FAULT_ID';

-- Expected: Fault details, should have NO existing WO
```

**Test Query:**
```bash
# API Call - Prefill
curl "http://localhost:8000/v1/actions/create_work_order_from_fault/prefill?fault_id=TEST_FAULT_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Prefill data with fault details
- Equipment pre-filled
- Priority suggested based on severity
- Duplicate check (should be false)

#### Step 2: Preview

**Test Query:**
```bash
# API Call - Preview
curl -X POST http://localhost:8000/v1/actions/create_work_order_from_fault/preview \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID"
    },
    "payload": {
      "fault_id": "TEST_FAULT_ID",
      "title": "Fix Generator E001 - High Temperature",
      "equipment_id": "TEST_EQUIPMENT_ID",
      "priority": "high",
      "description": "Investigate and resolve high temperature alarm"
    }
  }'
```

**Expected Result:**
- Preview shows what will be created
- Work order number predicted (WO-XXXXX)
- Side effects listed (fault will be linked)
- No database mutations yet

#### Step 3: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_work_order_from_fault",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "chief_engineer"
    },
    "payload": {
      "fault_id": "TEST_FAULT_ID",
      "title": "Fix Generator E001 - High Temperature",
      "equipment_id": "TEST_EQUIPMENT_ID",
      "priority": "high",
      "description": "Investigate and resolve high temperature alarm",
      "signature": {
        "user_id": "TEST_USER_ID",
        "action": "create_work_order_from_fault",
        "timestamp": "2026-01-09T10:30:00Z",
        "signature": "base64_encoded_signature_here"
      }
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Work order created
- Returns WO ID and number
- Message: "Work order WO-XXXXX created successfully"

**Verification Queries:**
```sql
-- Check work order was created
SELECT
  id,
  number,
  title,
  status,
  priority,
  equipment_id,
  fault_id,
  created_by,
  created_at
FROM pms_work_orders
WHERE fault_id = 'TEST_FAULT_ID';

-- Expected: 1 new work order with fault_id populated
```

```sql
-- Check audit log entry
SELECT
  action,
  entity_type,
  entity_id,
  user_id,
  signature,
  new_values,
  created_at
FROM pms_audit_log
WHERE action = 'create_work_order_from_fault'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: Audit entry with WHO/WHEN/WHAT
```

---

### Test 4: add_note_to_work_order (P0 Action #3 - MUTATE)

**Purpose:** Add progress note to work order
**API Endpoints:**
- `GET /v1/actions/add_note_to_work_order/prefill?work_order_id=...`
- `POST /v1/actions/execute` (action: add_note_to_work_order)

#### Step 1: Prefill

**Pre-Query Check:**
```sql
-- Get work order details
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.status,
  e.name as equipment_name,
  COUNT(n.id) as existing_notes
FROM pms_work_orders wo
INNER JOIN pms_equipment e ON e.id = wo.equipment_id
LEFT JOIN pms_work_order_notes n ON n.work_order_id = wo.id
WHERE wo.id = 'TEST_WO_ID'
GROUP BY wo.id, wo.number, wo.title, wo.status, e.name;

-- Expected: WO details with note count
```

**Test Query:**
```bash
# API Call - Prefill
curl "http://localhost:8000/v1/actions/add_note_to_work_order/prefill?work_order_id=TEST_WO_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Work order context
- Equipment name
- Current status
- Existing notes summary

#### Step 2: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_note_to_work_order",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "note_text": "Checked coolant levels - all normal. Coolant temperature sensor reading 85°C. Will investigate electrical connections next.",
      "note_type": "progress"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Note created
- Returns note ID and timestamp
- WHO added the note

**Verification Queries:**
```sql
-- Check note was created
SELECT
  id,
  work_order_id,
  note_text,
  note_type,
  created_by,
  created_at
FROM pms_work_order_notes
WHERE work_order_id = 'TEST_WO_ID'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: New note with correct text and user_id
```

```sql
-- Check audit log
SELECT
  action,
  entity_type,
  new_values->>'note_text' as note_preview,
  user_id,
  created_at
FROM pms_audit_log
WHERE action = 'add_note_to_work_order'
  AND (new_values->>'work_order_id')::uuid = 'TEST_WO_ID'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: Audit entry logged
```

---

### Test 5: add_part_to_work_order (P0 Action #4 - MUTATE)

**Purpose:** Add part to work order shopping list
**API Endpoints:**
- `GET /v1/actions/add_part_to_work_order/prefill?work_order_id=...&part_id=...`
- `POST /v1/actions/add_part_to_work_order/preview`
- `POST /v1/actions/execute` (action: add_part_to_work_order)

#### Step 1: Prefill

**Pre-Query Check:**
```sql
-- Check part stock availability
SELECT
  p.id,
  p.name,
  p.part_number,
  p.quantity_on_hand,
  p.minimum_quantity,
  p.unit,
  CASE
    WHEN p.quantity_on_hand <= p.minimum_quantity THEN 'LOW'
    WHEN p.quantity_on_hand > p.minimum_quantity * 2 THEN 'GOOD'
    ELSE 'ADEQUATE'
  END as stock_status
FROM pms_parts p
WHERE p.id = 'TEST_PART_ID';

-- Expected: Part with stock status
```

**Test Query:**
```bash
# API Call - Prefill
curl "http://localhost:8000/v1/actions/add_part_to_work_order/prefill?work_order_id=TEST_WO_ID&part_id=TEST_PART_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Part details
- Current stock level
- Stock availability status
- Suggested quantity: 1

#### Step 2: Preview

**Test Query:**
```bash
# API Call - Preview
curl -X POST http://localhost:8000/v1/actions/add_part_to_work_order/preview \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID"
    },
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "part_id": "TEST_PART_ID",
      "quantity": 2,
      "notes": "Replacement temperature sensors"
    }
  }'
```

**Expected Result:**
- Preview shows part will be added to shopping list
- Stock availability confirmed
- No immediate inventory deduction (happens on completion)

#### Step 3: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_part_to_work_order",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "part_id": "TEST_PART_ID",
      "quantity": 2,
      "notes": "Replacement temperature sensors"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Part added to shopping list
- Shopping list is JSON field on work order
- No inventory deduction yet

**Verification Queries:**
```sql
-- Check shopping list was updated (JSON field)
SELECT
  id,
  number,
  shopping_list
FROM pms_work_orders
WHERE id = 'TEST_WO_ID';

-- Expected: shopping_list JSON contains new part
-- Format: [{"part_id": "...", "quantity": 2, "notes": "...", "added_by": "...", "added_at": "..."}]
```

```sql
-- Verify inventory NOT deducted yet
SELECT quantity_on_hand
FROM pms_parts
WHERE id = 'TEST_PART_ID';

-- Expected: Quantity unchanged (deduction happens on WO completion)
```

---

### Test 6: log_part_usage (P0 Action #7 - MUTATE)

**Purpose:** Directly deduct inventory (not via WO completion)
**API Endpoints:**
- `GET /v1/actions/log_part_usage/prefill?part_id=...&work_order_id=...`
- `POST /v1/actions/log_part_usage/preview`
- `POST /v1/actions/execute` (action: log_part_usage)

#### Step 1: Get Current Stock

**Pre-Query Check:**
```sql
-- Record current stock BEFORE deduction
SELECT
  id,
  name,
  part_number,
  quantity_on_hand,
  minimum_quantity,
  unit
FROM pms_parts
WHERE id = 'TEST_PART_ID';

-- Save quantity_on_hand as: STOCK_BEFORE
```

#### Step 2: Prefill

**Test Query:**
```bash
# API Call - Prefill
curl "http://localhost:8000/v1/actions/log_part_usage/prefill?part_id=TEST_PART_ID&work_order_id=TEST_WO_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Part details
- Current stock
- Work order context (if provided)
- Suggested usage reason

#### Step 3: Preview

**Test Query:**
```bash
# API Call - Preview
curl -X POST http://localhost:8000/v1/actions/log_part_usage/preview \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID"
    },
    "payload": {
      "part_id": "TEST_PART_ID",
      "quantity": 3,
      "usage_reason": "maintenance",
      "work_order_id": "TEST_WO_ID",
      "notes": "Routine filter replacement"
    }
  }'
```

**Expected Result:**
- Shows stock before and after deduction
- Warns if stock will be low
- Shows usage will be logged

#### Step 4: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "log_part_usage",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "part_id": "TEST_PART_ID",
      "quantity": 3,
      "usage_reason": "maintenance",
      "work_order_id": "TEST_WO_ID",
      "equipment_id": "TEST_EQUIPMENT_ID",
      "notes": "Routine filter replacement"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Inventory deducted atomically
- Usage logged
- Returns stock_before and stock_after

**Verification Queries:**
```sql
-- Check inventory was deducted
SELECT
  name,
  quantity_on_hand,
  (quantity_on_hand = STOCK_BEFORE - 3) as correct_deduction
FROM pms_parts
WHERE id = 'TEST_PART_ID';

-- Expected: quantity_on_hand = STOCK_BEFORE - 3
```

```sql
-- Check usage log entry
SELECT
  part_id,
  quantity,
  stock_before,
  stock_after,
  usage_reason,
  work_order_id,
  equipment_id,
  used_by,
  used_at,
  notes
FROM pms_part_usage
WHERE part_id = 'TEST_PART_ID'
ORDER BY used_at DESC
LIMIT 1;

-- Expected: Usage logged with all details
```

```sql
-- Check audit log
SELECT
  action,
  entity_type,
  new_values->'part_usage' as usage_details,
  user_id,
  created_at
FROM pms_audit_log
WHERE action = 'log_part_usage'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: Audit entry with WHO/WHEN/WHAT
```

---

### Test 7: mark_work_order_complete (P0 Action #5 - MUTATE + Signature)

**Purpose:** Complete work order and deduct all parts from shopping list
**API Endpoints:**
- `GET /v1/actions/mark_work_order_complete/prefill?work_order_id=...`
- `POST /v1/actions/mark_work_order_complete/preview`
- `POST /v1/actions/execute` (action: mark_work_order_complete)

#### Step 1: Setup

**Pre-Query Check:**
```sql
-- Get work order with parts in shopping list
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.status,
  wo.shopping_list,
  e.name as equipment_name
FROM pms_work_orders wo
INNER JOIN pms_equipment e ON e.id = wo.equipment_id
WHERE wo.id = 'TEST_WO_ID';

-- Expected: WO with status 'in_progress' and shopping_list populated
```

```sql
-- Record stock levels BEFORE completion
SELECT
  p.id,
  p.name,
  p.quantity_on_hand
FROM pms_parts p
WHERE p.id IN (
  -- Extract part IDs from shopping_list JSON
  SELECT (item->>'part_id')::uuid
  FROM pms_work_orders,
  jsonb_array_elements(shopping_list) as item
  WHERE id = 'TEST_WO_ID'
);

-- Save these quantities as: PARTS_STOCK_BEFORE
```

#### Step 2: Prefill

**Test Query:**
```bash
# API Call - Prefill
curl "http://localhost:8000/v1/actions/mark_work_order_complete/prefill?work_order_id=TEST_WO_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Work order summary
- Parts list from shopping list
- Current stock levels for each part
- Warnings if any part has insufficient stock

#### Step 3: Preview

**Test Query:**
```bash
# API Call - Preview
curl -X POST http://localhost:8000/v1/actions/mark_work_order_complete/preview \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID"
    },
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "completion_notes": "Generator temperature issue resolved. Replaced 2 faulty temperature sensors. System monitored for 2 hours - operating normally. Coolant levels checked and topped up.",
      "parts_used": [
        {
          "part_id": "TEST_PART_ID",
          "quantity": 2
        }
      ],
      "signature": {
        "user_id": "TEST_USER_ID",
        "action": "mark_work_order_complete",
        "timestamp": "2026-01-09T12:00:00Z"
      }
    }
  }'
```

**Expected Result:**
- Shows WO will be marked complete
- Shows inventory deductions for each part
- Shows stock levels after deduction
- Warns if any stock will be low

#### Step 4: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "mark_work_order_complete",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "chief_engineer"
    },
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "completion_notes": "Generator temperature issue resolved. Replaced 2 faulty temperature sensors. System monitored for 2 hours - operating normally. Coolant levels checked and topped up.",
      "parts_used": [
        {
          "part_id": "TEST_PART_ID",
          "quantity": 2
        }
      ],
      "signature": {
        "user_id": "TEST_USER_ID",
        "action": "mark_work_order_complete",
        "timestamp": "2026-01-09T12:00:00Z",
        "signature": "base64_encoded_signature_here"
      }
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Work order marked complete
- All parts deducted from inventory
- Returns inventory deduction summary

**Verification Queries:**
```sql
-- Check work order was completed
SELECT
  id,
  number,
  status,
  completed_by,
  completed_at,
  completion_notes
FROM pms_work_orders
WHERE id = 'TEST_WO_ID';

-- Expected: status = 'completed', completed_by = TEST_USER_ID, completion_notes populated
```

```sql
-- Check inventory was deducted
SELECT
  p.id,
  p.name,
  p.quantity_on_hand,
  pu.quantity as deducted_qty,
  pu.stock_before,
  pu.stock_after
FROM pms_parts p
INNER JOIN pms_part_usage pu ON pu.part_id = p.id
WHERE pu.work_order_id = 'TEST_WO_ID'
  AND pu.used_at >= NOW() - INTERVAL '1 minute';

-- Expected: Deductions logged, stock reduced correctly
```

```sql
-- Check all parts have usage log entries
SELECT
  p.name,
  pu.quantity,
  pu.stock_before,
  pu.stock_after,
  pu.used_by,
  pu.used_at
FROM pms_part_usage pu
INNER JOIN pms_parts p ON p.id = pu.part_id
WHERE pu.work_order_id = 'TEST_WO_ID'
ORDER BY pu.used_at DESC;

-- Expected: One entry per part used
```

```sql
-- Check audit log entry
SELECT
  action,
  entity_type,
  entity_id,
  user_id,
  signature,
  new_values->'completion_notes' as notes,
  new_values->'inventory_deductions' as deductions,
  created_at
FROM pms_audit_log
WHERE action = 'mark_work_order_complete'
  AND entity_id = 'TEST_WO_ID'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: Complete audit with signature and deductions
```

---

### Test 8: add_to_handover (P0 Action #8 - MUTATE)

**Purpose:** Add item to shift handover list
**API Endpoints:**
- `GET /v1/actions/add_to_handover/prefill?entity_type=...&entity_id=...`
- `POST /v1/actions/execute` (action: add_to_handover)

#### Step 1: Prefill (Auto-generate summary)

**Test Query:**
```bash
# API Call - Prefill from work order
curl "http://localhost:8000/v1/actions/add_to_handover/prefill?entity_type=work_order&entity_id=TEST_WO_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Result:**
- Auto-generated summary from WO
- Category: "work_in_progress"
- Equipment name and location
- Priority suggested

#### Step 2: Execute

**Test Query:**
```bash
# API Call - Execute
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_to_handover",
    "context": {
      "yacht_id": "TEST_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "chief_engineer"
    },
    "payload": {
      "entity_type": "work_order",
      "entity_id": "TEST_WO_ID",
      "summary_text": "Generator E001 issue resolved. Replaced 2 temperature sensors. System monitored and operating normally. No further action required.",
      "category": "work_in_progress",
      "priority": "normal"
    }
  }'
```

**Expected Result:**
- Status: 200 OK
- Handover entry created
- Returns entry ID and timestamp
- WHO added it

**Verification Queries:**
```sql
-- Check handover entry was created
SELECT
  id,
  entity_type,
  entity_id,
  summary_text,
  category,
  priority,
  added_by,
  added_at
FROM pms_handover
WHERE entity_id = 'TEST_WO_ID'
  AND entity_type = 'work_order'
ORDER BY added_at DESC
LIMIT 1;

-- Expected: Handover entry with all details
```

```sql
-- Get user who added it
SELECT
  h.summary_text,
  h.added_at,
  u.full_name as added_by_name
FROM pms_handover h
INNER JOIN user_profiles u ON u.id = h.added_by
WHERE h.entity_id = 'TEST_WO_ID'
ORDER BY h.added_at DESC
LIMIT 1;

-- Expected: Handover with user name
```

```sql
-- Check audit log
SELECT
  action,
  entity_type,
  new_values->'entity_type' as handover_entity_type,
  new_values->'category' as category,
  user_id,
  created_at
FROM pms_audit_log
WHERE action = 'add_to_handover'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: Audit entry logged
```

---

## Situation Triggers

### Trigger 1: "Fix Something" Situation

**Scenario:** User searches for fault or equipment issue

**Search Query Examples:**
- "generator high temperature"
- "engine alarm E001"
- "fault on main generator"

**Expected Trigger:**
```json
{
  "situation": "fix_something",
  "entities": {
    "equipment": ["main_generator"],
    "fault_code": ["E001"]
  },
  "actions_available": [
    {
      "action": "show_manual_section",
      "label": "View Manual",
      "priority": 1
    },
    {
      "action": "create_work_order_from_fault",
      "label": "Create Work Order",
      "priority": 2
    }
  ]
}
```

**Verification Query:**
```sql
-- Check what faults match the search
SELECT
  f.id,
  f.fault_code,
  f.title,
  f.severity,
  e.name as equipment_name,
  e.location
FROM pms_faults f
INNER JOIN pms_equipment e ON e.id = f.equipment_id
WHERE f.status = 'open'
  AND (
    f.title ILIKE '%temperature%'
    OR f.fault_code ILIKE '%E001%'
    OR e.name ILIKE '%generator%'
  );

-- Expected: Matching faults that should trigger "fix_something" situation
```

---

### Trigger 2: "Do Maintenance" Situation

**Scenario:** User is working on an active work order

**Search Query Examples:**
- "work order 42"
- "WO-42 progress"
- "generator maintenance"

**Expected Trigger:**
```json
{
  "situation": "do_maintenance",
  "entities": {
    "work_order": ["WO-42"],
    "equipment": ["main_generator"]
  },
  "actions_available": [
    {
      "action": "add_note_to_work_order",
      "label": "Add Progress Note",
      "priority": 1
    },
    {
      "action": "add_part_to_work_order",
      "label": "Add Part",
      "priority": 2
    },
    {
      "action": "mark_work_order_complete",
      "label": "Complete Work Order",
      "priority": 3
    }
  ]
}
```

**Verification Query:**
```sql
-- Check active work orders
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.status,
  e.name as equipment_name,
  COUNT(n.id) as note_count
FROM pms_work_orders wo
INNER JOIN pms_equipment e ON e.id = wo.equipment_id
LEFT JOIN pms_work_order_notes n ON n.work_order_id = wo.id
WHERE wo.status IN ('pending', 'in_progress')
  AND wo.yacht_id = 'TEST_YACHT_ID'
GROUP BY wo.id, wo.number, wo.title, wo.status, e.name
ORDER BY wo.created_at DESC;

-- Expected: Active WOs that should trigger "do_maintenance" situation
```

---

### Trigger 3: "Inventory/Parts" Situation

**Scenario:** User searches for parts or checks stock

**Search Query Examples:**
- "oil filter stock"
- "check filter inventory"
- "part OF-12345"

**Expected Trigger:**
```json
{
  "situation": "inventory_parts",
  "entities": {
    "part": ["oil_filter", "OF-12345"]
  },
  "actions_available": [
    {
      "action": "check_stock_level",
      "label": "Check Stock",
      "priority": 1
    },
    {
      "action": "log_part_usage",
      "label": "Log Usage",
      "priority": 2
    }
  ]
}
```

**Verification Query:**
```sql
-- Check parts matching search
SELECT
  p.id,
  p.name,
  p.part_number,
  p.quantity_on_hand,
  p.minimum_quantity,
  p.location,
  CASE
    WHEN p.quantity_on_hand <= p.minimum_quantity THEN 'LOW'
    ELSE 'OK'
  END as stock_status
FROM pms_parts p
WHERE p.yacht_id = 'TEST_YACHT_ID'
  AND (
    p.name ILIKE '%filter%'
    OR p.part_number ILIKE '%OF-12345%'
  );

-- Expected: Parts that should trigger "inventory_parts" situation
```

---

### Trigger 4: "Handover Communication" Situation

**Scenario:** End of shift, preparing handover

**Search Query Examples:**
- "shift handover"
- "what needs handover"
- "handover items"

**Expected Trigger:**
```json
{
  "situation": "handover_communication",
  "actions_available": [
    {
      "action": "add_to_handover",
      "label": "Add to Handover",
      "priority": 1
    }
  ]
}
```

**Verification Query:**
```sql
-- Check current handover items for today
SELECT
  h.id,
  h.entity_type,
  h.summary_text,
  h.category,
  h.priority,
  h.added_at,
  u.full_name as added_by_name
FROM pms_handover h
INNER JOIN user_profiles u ON u.id = h.added_by
WHERE h.yacht_id = 'TEST_YACHT_ID'
  AND h.added_at >= CURRENT_DATE
ORDER BY h.priority DESC, h.added_at DESC;

-- Expected: Today's handover items by priority
```

---

## Audit Trail Verification

### Complete Audit History for Work Order

```sql
-- Get complete audit trail for a work order lifecycle
WITH wo_audit AS (
  SELECT
    al.action,
    al.created_at,
    al.user_id,
    u.full_name,
    al.new_values
  FROM pms_audit_log al
  INNER JOIN user_profiles u ON u.id = al.user_id
  WHERE al.entity_id = 'TEST_WO_ID'
    OR (al.new_values->>'work_order_id')::uuid = 'TEST_WO_ID'
)
SELECT
  action,
  created_at,
  full_name as performed_by,
  new_values
FROM wo_audit
ORDER BY created_at ASC;

-- Expected: Complete timeline of all actions on WO
-- create_work_order_from_fault → add_note → add_part → log_part_usage → mark_complete
```

### Inventory Audit Trail

```sql
-- Track all inventory movements for a part
SELECT
  pu.used_at,
  pu.quantity,
  pu.stock_before,
  pu.stock_after,
  pu.usage_reason,
  wo.number as work_order_number,
  e.name as equipment_name,
  u.full_name as used_by_name
FROM pms_part_usage pu
LEFT JOIN pms_work_orders wo ON wo.id = pu.work_order_id
LEFT JOIN pms_equipment e ON e.id = pu.equipment_id
INNER JOIN user_profiles u ON u.id = pu.used_by
WHERE pu.part_id = 'TEST_PART_ID'
ORDER BY pu.used_at DESC
LIMIT 20;

-- Expected: Complete usage history with WHO/WHEN/WHAT/WHERE/WHY
```

### User Activity Report

```sql
-- Get all actions performed by a user today
SELECT
  al.action,
  al.entity_type,
  al.created_at,
  al.new_values->>'title' as action_title,
  al.new_values->>'note_text' as note_preview
FROM pms_audit_log al
WHERE al.user_id = 'TEST_USER_ID'
  AND al.created_at >= CURRENT_DATE
ORDER BY al.created_at DESC;

-- Expected: Today's activity for accountability tracking
```

---

## Edge Cases

### Edge Case 1: Insufficient Stock

**Scenario:** Try to complete WO but not enough stock

**Setup Query:**
```sql
-- Create low stock scenario
UPDATE pms_parts
SET quantity_on_hand = 1
WHERE id = 'TEST_PART_ID';
```

**Test Query:**
```bash
# Try to complete WO requiring 2 parts (but only 1 in stock)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "mark_work_order_complete",
    "context": {"yacht_id": "TEST_YACHT_ID", "user_id": "TEST_USER_ID", "role": "chief_engineer"},
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "completion_notes": "Attempting completion with insufficient stock",
      "parts_used": [{"part_id": "TEST_PART_ID", "quantity": 2}],
      "signature": {"user_id": "TEST_USER_ID", "action": "mark_work_order_complete", "timestamp": "2026-01-09T10:00:00Z"}
    }
  }'
```

**Expected Result:**
- Status: 400 Bad Request
- Error code: "INSUFFICIENT_STOCK"
- Message: "Not enough stock for Part Name. Available: 1, Required: 2"
- NO inventory deduction
- NO work order status change

**Verification Query:**
```sql
-- Verify NO changes occurred
SELECT
  wo.status,
  p.quantity_on_hand
FROM pms_work_orders wo, pms_parts p
WHERE wo.id = 'TEST_WO_ID'
  AND p.id = 'TEST_PART_ID';

-- Expected: status still 'in_progress', stock still 1
```

---

### Edge Case 2: Duplicate Work Order Prevention

**Scenario:** Try to create WO for fault that already has WO

**Test Query:**
```bash
# Try to create duplicate WO
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_work_order_from_fault",
    "context": {"yacht_id": "TEST_YACHT_ID", "user_id": "TEST_USER_ID", "role": "chief_engineer"},
    "payload": {
      "fault_id": "TEST_FAULT_ID",
      "title": "Duplicate WO attempt",
      "priority": "high",
      "signature": {"user_id": "TEST_USER_ID", "action": "create_work_order_from_fault", "timestamp": "2026-01-09T10:00:00Z"},
      "override_duplicate": false
    }
  }'
```

**Expected Result:**
- Status: 400 Bad Request
- Error code: "DUPLICATE_WO_EXISTS"
- Message: "Work order WO-XXX already exists for this fault"
- NO new work order created

**Verification Query:**
```sql
-- Verify only ONE WO exists for fault
SELECT COUNT(*) as wo_count
FROM pms_work_orders
WHERE fault_id = 'TEST_FAULT_ID';

-- Expected: 1 (original WO, no duplicate)
```

---

### Edge Case 3: Closed Work Order Write Prevention

**Scenario:** Try to add note to completed WO

**Setup Query:**
```sql
-- Mark WO as completed
UPDATE pms_work_orders
SET status = 'completed',
    completed_by = 'TEST_USER_ID',
    completed_at = NOW()
WHERE id = 'TEST_WO_ID';
```

**Test Query:**
```bash
# Try to add note to closed WO
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_note_to_work_order",
    "context": {"yacht_id": "TEST_YACHT_ID", "user_id": "TEST_USER_ID", "role": "engineer"},
    "payload": {
      "work_order_id": "TEST_WO_ID",
      "note_text": "Attempting to add note to closed WO",
      "note_type": "progress"
    }
  }'
```

**Expected Result:**
- Status: 400 Bad Request
- Error code: "WO_CLOSED"
- Message: "Cannot modify closed work order"
- NO note created

**Verification Query:**
```sql
-- Verify NO new notes after WO closed
SELECT COUNT(*) as notes_after_completion
FROM pms_work_order_notes
WHERE work_order_id = 'TEST_WO_ID'
  AND created_at > (
    SELECT completed_at
    FROM pms_work_orders
    WHERE id = 'TEST_WO_ID'
  );

-- Expected: 0 (no notes added after completion)
```

---

### Edge Case 4: Invalid Signature Rejection

**Scenario:** Try to create WO with invalid signature

**Test Query:**
```bash
# Submit with missing signature
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_work_order_from_fault",
    "context": {"yacht_id": "TEST_YACHT_ID", "user_id": "TEST_USER_ID", "role": "chief_engineer"},
    "payload": {
      "fault_id": "TEST_FAULT_ID",
      "title": "Test WO",
      "priority": "high"
    }
  }'
```

**Expected Result:**
- Status: 400 Bad Request
- Error code: "INVALID_SIGNATURE"
- Message: "Signature required for this action"
- NO work order created

---

### Edge Case 5: Yacht Isolation Violation

**Scenario:** Try to access another yacht's data

**Test Query:**
```bash
# Try to check stock for part from DIFFERENT yacht
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "check_stock_level",
    "context": {
      "yacht_id": "DIFFERENT_YACHT_ID",
      "user_id": "TEST_USER_ID",
      "role": "engineer"
    },
    "payload": {
      "part_id": "PART_FROM_DIFFERENT_YACHT"
    }
  }'
```

**Expected Result:**
- Status: 403 Forbidden
- Error code: "YACHT_ISOLATION_VIOLATION"
- Message: "Access denied: yacht mismatch"
- NO data returned

---

## Summary Test Checklist

### READ Actions (No Side Effects)
- [ ] show_manual_section - Returns manual, no DB changes
- [ ] check_stock_level - Returns stock info, no DB changes

### MUTATE Actions (Create Audit Logs)
- [ ] create_work_order_from_fault - Creates WO, logs audit
- [ ] add_note_to_work_order - Creates note, logs audit
- [ ] add_part_to_work_order - Updates shopping list, logs audit
- [ ] log_part_usage - Deducts inventory, logs audit + usage
- [ ] mark_work_order_complete - Completes WO, deducts all parts, logs audit + usage
- [ ] add_to_handover - Creates handover entry, logs audit

### Accountability Verification
- [ ] All MUTATE actions have WHO (user_id)
- [ ] All MUTATE actions have WHEN (timestamps)
- [ ] All MUTATE actions have WHAT (audit log new_values)
- [ ] Signature validation works for create_work_order_from_fault
- [ ] Signature validation works for mark_work_order_complete

### Transparency Verification
- [ ] Preview endpoints show exact changes
- [ ] Audit log captures old_values + new_values
- [ ] Inventory changes show stock_before and stock_after
- [ ] Side effects listed in preview

### Edge Cases Verification
- [ ] Insufficient stock prevents completion
- [ ] Duplicate WO detection works
- [ ] Closed WO prevents modifications
- [ ] Invalid signature rejected
- [ ] Yacht isolation enforced

---

**END OF TEST QUERIES DOCUMENT**
