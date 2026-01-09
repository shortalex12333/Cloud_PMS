# Supabase Pre-Flight Database Checks

**Date:** 2026-01-09
**Purpose:** Verify database integrity before frontend testing
**Execute in:** Supabase SQL Editor (https://app.supabase.com/project/ymhpscejjmcbwyknxiwb/sql)

---

## 🎯 Overview

Run these checks IN ORDER to ensure the database is ready for frontend testing. Each check verifies critical functionality that the frontend depends on.

**Estimated Time:** 15-20 minutes

---

## ✅ CHECK 1: Migration Status

**Purpose:** Verify all migrations deployed successfully

```sql
-- Check if new accountability columns exist on pms_parts
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pms_parts'
  AND column_name IN (
    'quantity_on_hand',
    'minimum_quantity',
    'unit',
    'location',
    'last_counted_at',
    'last_counted_by'
  )
ORDER BY column_name;
```

**Expected Result:** 6 rows returned

```
✅ PASS: 6 columns found
❌ FAIL: Less than 6 columns found → Re-run migration 03
```

---

```sql
-- Check if new accountability columns exist on pms_work_orders
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pms_work_orders'
  AND column_name IN (
    'fault_id',
    'assigned_to',
    'completed_by',
    'completed_at',
    'completion_notes'
  )
ORDER BY column_name;
```

**Expected Result:** 5 rows returned

```
✅ PASS: 5 columns found
❌ FAIL: Less than 5 columns found → Re-run migration 03
```

---

```sql
-- Check if new trust tables exist
SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN (
    'pms_audit_log',
    'pms_part_usage',
    'pms_work_order_notes',
    'pms_handover'
  )
ORDER BY table_name;
```

**Expected Result:** 4 tables returned

```
✅ PASS: All 4 tables found
❌ FAIL: Missing tables → Re-run migration 04
```

---

## ✅ CHECK 2: Data Existence

**Purpose:** Ensure you have test data to work with

```sql
-- Check for yachts/vessels
SELECT
  'yachts' as source,
  COUNT(*) as count
FROM yachts
WHERE deleted_at IS NULL

UNION ALL

SELECT
  'vessels' as source,
  COUNT(*) as count
FROM vessels
WHERE deleted_at IS NULL;
```

**Expected Result:** At least 1 yacht/vessel

```
✅ PASS: Count > 0
❌ FAIL: Count = 0 → Create test yacht
```

**If FAIL, create test yacht:**
```sql
INSERT INTO yachts (id, name, created_at)
VALUES (gen_random_uuid(), 'Test Yacht Alpha', NOW())
RETURNING id, name;

-- Save the returned ID as TEST_YACHT_ID
```

---

```sql
-- Check for equipment
SELECT COUNT(*) as equipment_count
FROM pms_equipment
WHERE deleted_at IS NULL;
```

**Expected Result:** At least 1 equipment item

```
✅ PASS: Count > 0
❌ FAIL: Count = 0 → Create test equipment (see below)
```

**If FAIL, create test equipment:**
```sql
-- First get a yacht_id
WITH yacht AS (
  SELECT id FROM yachts LIMIT 1
)
INSERT INTO pms_equipment (
  id,
  yacht_id,
  name,
  equipment_type,
  manufacturer,
  model,
  location,
  status,
  created_at
)
SELECT
  gen_random_uuid(),
  yacht.id,
  'Main Generator',
  'generator',
  'Caterpillar',
  'C18',
  'Engine Room',
  'operational',
  NOW()
FROM yacht
RETURNING id, name, location;

-- Save the returned ID as TEST_EQUIPMENT_ID
```

---

```sql
-- Check for faults
SELECT COUNT(*) as open_faults
FROM pms_faults
WHERE status = 'open'
  AND deleted_at IS NULL;
```

**Expected Result:** At least 1 open fault

```
✅ PASS: Count > 0
❌ FAIL: Count = 0 → Create test fault (see below)
```

**If FAIL, create test fault:**
```sql
-- Get yacht and equipment IDs
WITH context AS (
  SELECT
    y.id as yacht_id,
    e.id as equipment_id,
    u.id as user_id
  FROM yachts y
  CROSS JOIN pms_equipment e
  CROSS JOIN user_profiles u
  WHERE y.deleted_at IS NULL
    AND e.deleted_at IS NULL
  LIMIT 1
)
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
  reported_at,
  created_at
)
SELECT
  gen_random_uuid(),
  yacht_id,
  equipment_id,
  'E001',
  'High Temperature Alarm',
  'Generator coolant temperature exceeds normal operating range. Requires immediate investigation.',
  'high',
  'open',
  user_id,
  NOW(),
  NOW()
FROM context
RETURNING id, fault_code, title;

-- Save the returned ID as TEST_FAULT_ID
```

---

```sql
-- Check for parts with inventory
SELECT COUNT(*) as parts_with_stock
FROM pms_parts
WHERE quantity_on_hand > 0
  AND deleted_at IS NULL;
```

**Expected Result:** At least 1 part with stock

```
✅ PASS: Count > 0
❌ FAIL: Count = 0 → Create test part (see below)
```

**If FAIL, create test part:**
```sql
-- Get yacht_id
WITH yacht AS (
  SELECT id FROM yachts LIMIT 1
)
INSERT INTO pms_parts (
  id,
  yacht_id,
  name,
  part_number,
  category,
  quantity_on_hand,
  minimum_quantity,
  unit,
  location,
  created_at
)
SELECT
  gen_random_uuid(),
  yacht.id,
  'Oil Filter',
  'OF-12345',
  'filters',
  20,
  5,
  'pieces',
  'Engine Room - Shelf A2',
  NOW()
FROM yacht
RETURNING id, name, part_number, quantity_on_hand;

-- Save the returned ID as TEST_PART_ID
```

---

```sql
-- Check for users
SELECT COUNT(*) as user_count
FROM user_profiles;
```

**Expected Result:** At least 1 user

```
✅ PASS: Count > 0
❌ FAIL: Count = 0 → Create user via Supabase Auth dashboard
```

---

## ✅ CHECK 3: Foreign Key Integrity

**Purpose:** Ensure relationships between tables are valid

```sql
-- Check for orphaned faults (equipment doesn't exist)
SELECT
  f.id,
  f.fault_code,
  f.title,
  f.equipment_id
FROM pms_faults f
LEFT JOIN pms_equipment e ON e.id = f.equipment_id
WHERE f.deleted_at IS NULL
  AND e.id IS NULL;
```

**Expected Result:** 0 rows (no orphans)

```
✅ PASS: No orphaned faults
❌ FAIL: Orphaned faults found → Delete or fix them
```

**If FAIL, fix orphaned faults:**
```sql
-- Delete orphaned faults
DELETE FROM pms_faults
WHERE id IN (
  SELECT f.id
  FROM pms_faults f
  LEFT JOIN pms_equipment e ON e.id = f.equipment_id
  WHERE f.deleted_at IS NULL
    AND e.id IS NULL
);
```

---

```sql
-- Check for orphaned work orders (equipment doesn't exist)
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.equipment_id
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON e.id = wo.equipment_id
WHERE wo.deleted_at IS NULL
  AND e.id IS NULL;
```

**Expected Result:** 0 rows (no orphans)

```
✅ PASS: No orphaned work orders
❌ FAIL: Orphaned work orders found → Fix them
```

---

```sql
-- Check for parts with invalid yacht_id
SELECT
  p.id,
  p.name,
  p.yacht_id
FROM pms_parts p
LEFT JOIN yachts y ON y.id = p.yacht_id
WHERE p.deleted_at IS NULL
  AND y.id IS NULL;
```

**Expected Result:** 0 rows (no invalid references)

```
✅ PASS: All parts have valid yacht_id
❌ FAIL: Invalid yacht references found → Fix them
```

---

## ✅ CHECK 4: Enum Values

**Purpose:** Verify enum types have expected values

```sql
-- Check work_order_status enum
SELECT
  enumlabel as status_value
FROM pg_enum
WHERE enumtypid = 'work_order_status'::regtype
ORDER BY enumsortorder;
```

**Expected Result:**
```
candidate
pending
in_progress
completed
cancelled
```

```
✅ PASS: All 5 statuses present, NO 'closed' value
❌ FAIL: 'closed' value exists or other values missing → Check migration
```

---

```sql
-- Check fault severity enum
SELECT
  enumlabel as severity_value
FROM pg_enum
WHERE enumtypid = 'fault_severity'::regtype
ORDER BY enumsortorder;
```

**Expected Result:**
```
low
medium
high
critical
```

```
✅ PASS: All 4 severities present
❌ FAIL: Values missing → Check enum definition
```

---

## ✅ CHECK 5: Default Values & Constraints

**Purpose:** Ensure columns have correct defaults and constraints

```sql
-- Check pms_parts has correct defaults for new columns
SELECT
  column_name,
  column_default,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'pms_parts'
  AND column_name IN ('quantity_on_hand', 'minimum_quantity', 'unit')
ORDER BY column_name;
```

**Expected Result:**
```
quantity_on_hand | 0     | YES
minimum_quantity | 0     | YES
unit             | NULL  | YES
```

```
✅ PASS: Defaults are correct
❌ FAIL: Incorrect defaults → Update with ALTER TABLE
```

---

```sql
-- Check NOT NULL constraints on critical fields
SELECT
  table_name,
  column_name,
  is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    (table_name = 'pms_audit_log' AND column_name IN ('action', 'entity_type', 'user_id'))
    OR (table_name = 'pms_part_usage' AND column_name IN ('part_id', 'quantity', 'used_by'))
    OR (table_name = 'pms_work_order_notes' AND column_name IN ('work_order_id', 'note_text', 'created_by'))
  )
ORDER BY table_name, column_name;
```

**Expected Result:** All should be `is_nullable = NO`

```
✅ PASS: Critical fields are NOT NULL
❌ FAIL: Some fields allow NULL → Add constraints
```

---

## ✅ CHECK 6: Index Existence

**Purpose:** Verify performance indexes exist

```sql
-- Check for important indexes
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('pms_work_orders', 'pms_faults', 'pms_parts', 'pms_audit_log')
  AND indexname LIKE '%idx%'
ORDER BY tablename, indexname;
```

**Expected Result:** Multiple indexes returned

```
✅ PASS: Indexes exist (especially on yacht_id, status, equipment_id)
⚠️  WARN: Few indexes → Performance may be slow, but not critical
```

---

## ✅ CHECK 7: RLS (Row Level Security) Status

**Purpose:** Verify RLS is enabled for yacht isolation

```sql
-- Check RLS status on critical tables
SELECT
  schemaname,
  tablename,
  rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'pms_equipment',
    'pms_faults',
    'pms_work_orders',
    'pms_parts',
    'pms_audit_log',
    'pms_part_usage',
    'pms_handover'
  )
ORDER BY tablename;
```

**Expected Result:** All should have `rls_enabled = true`

```
✅ PASS: RLS enabled on all tables
⚠️  WARN: RLS disabled → Yacht isolation not enforced (security issue)
```

**If WARN, enable RLS:**
```sql
-- Enable RLS on all P0 tables
ALTER TABLE pms_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_part_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_work_order_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_handover ENABLE ROW LEVEL SECURITY;
```

---

```sql
-- Check RLS policies exist
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('pms_equipment', 'pms_faults', 'pms_work_orders', 'pms_parts')
ORDER BY tablename, policyname;
```

**Expected Result:** Policies exist for each table

```
✅ PASS: RLS policies found
⚠️  WARN: No policies → RLS is enabled but not enforced (users can't access data)
```

---

## ✅ CHECK 8: Sample Data Integrity

**Purpose:** Verify existing data makes sense

```sql
-- Check for work orders without equipment
SELECT
  wo.id,
  wo.number,
  wo.title,
  wo.equipment_id
FROM pms_work_orders wo
WHERE wo.equipment_id IS NULL
  AND wo.deleted_at IS NULL;
```

**Expected Result:** 0 rows (all WOs should have equipment)

```
✅ PASS: All work orders have equipment
⚠️  WARN: Some WOs missing equipment → Data quality issue
```

---

```sql
-- Check for parts with negative stock
SELECT
  id,
  name,
  part_number,
  quantity_on_hand,
  minimum_quantity
FROM pms_parts
WHERE quantity_on_hand < 0
  AND deleted_at IS NULL;
```

**Expected Result:** 0 rows (stock can't be negative)

```
✅ PASS: No negative stock
❌ FAIL: Negative stock found → Data corruption, fix immediately
```

**If FAIL, fix negative stock:**
```sql
-- Reset negative stock to 0
UPDATE pms_parts
SET quantity_on_hand = 0
WHERE quantity_on_hand < 0;
```

---

```sql
-- Check for completed work orders without completion_notes
SELECT
  id,
  number,
  title,
  status,
  completion_notes
FROM pms_work_orders
WHERE status = 'completed'
  AND (completion_notes IS NULL OR LENGTH(completion_notes) < 10)
  AND deleted_at IS NULL;
```

**Expected Result:** 0 rows (completed WOs must have notes)

```
✅ PASS: All completed WOs have notes
⚠️  WARN: Some completed WOs missing notes → Data created before migration
```

---

## ✅ CHECK 9: PostgreSQL Function

**Purpose:** Verify helper function exists

```sql
-- Check if deduct_part_inventory function exists
SELECT
  routine_name,
  routine_type,
  data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'deduct_part_inventory';
```

**Expected Result:** 1 row returned

```
✅ PASS: Function exists
❌ FAIL: Function missing → Re-run migration 04
```

---

```sql
-- Test function with dry-run (should fail if stock insufficient)
-- This is a safe test that won't modify data
SELECT deduct_part_inventory(
  p_yacht_id := (SELECT id FROM yachts LIMIT 1),
  p_part_id := (SELECT id FROM pms_parts WHERE quantity_on_hand > 0 LIMIT 1),
  p_quantity := 999999,  -- Intentionally too high
  p_work_order_id := NULL,
  p_equipment_id := NULL,
  p_usage_reason := 'test',
  p_notes := 'dry run test',
  p_used_by := (SELECT id FROM user_profiles LIMIT 1)
);
```

**Expected Result:** NULL (insufficient stock returns NULL)

```
✅ PASS: Function returns NULL for insufficient stock
❌ FAIL: Function errors or returns value → Function broken
```

---

## ✅ CHECK 10: Authentication Setup

**Purpose:** Verify you have a test user account

```sql
-- Check if you have a user profile
SELECT
  id,
  email,
  full_name,
  role,
  yacht_id
FROM user_profiles
WHERE deleted_at IS NULL
LIMIT 5;
```

**Expected Result:** At least 1 user with yacht_id

```
✅ PASS: User profiles exist with yacht_id
❌ FAIL: No users → Create user account in Supabase Auth
```

---

## 🎯 Pre-Flight Checklist Summary

After running all checks, verify:

- [ ] ✅ CHECK 1: All migrations deployed (6 + 5 columns, 4 tables)
- [ ] ✅ CHECK 2: Test data exists (yacht, equipment, fault, part, user)
- [ ] ✅ CHECK 3: No orphaned records (all foreign keys valid)
- [ ] ✅ CHECK 4: Enums are correct (no 'closed' status)
- [ ] ✅ CHECK 5: Defaults and constraints correct
- [ ] ✅ CHECK 6: Indexes exist (performance)
- [ ] ✅ CHECK 7: RLS enabled with policies
- [ ] ✅ CHECK 8: Data integrity (no negative stock, completed WOs have notes)
- [ ] ✅ CHECK 9: PostgreSQL function exists and works
- [ ] ✅ CHECK 10: Test user account exists

---

## 📝 Record Your Test Entity IDs

Save these IDs for frontend testing:

```
TEST_YACHT_ID: ________________________________
TEST_USER_ID: _________________________________
TEST_EQUIPMENT_ID: ____________________________
TEST_FAULT_ID: ________________________________
TEST_PART_ID: _________________________________
TEST_WO_ID: ___________________________________
```

**How to get them:**
```sql
-- Copy/paste this and save the results
SELECT
  'YACHT' as entity,
  id,
  name as description
FROM yachts
WHERE deleted_at IS NULL
LIMIT 1

UNION ALL

SELECT
  'USER' as entity,
  id,
  email as description
FROM user_profiles
LIMIT 1

UNION ALL

SELECT
  'EQUIPMENT' as entity,
  id,
  name as description
FROM pms_equipment
WHERE deleted_at IS NULL
LIMIT 1

UNION ALL

SELECT
  'FAULT' as entity,
  f.id,
  f.fault_code || ': ' || f.title as description
FROM pms_faults f
WHERE f.status = 'open'
  AND f.deleted_at IS NULL
LIMIT 1

UNION ALL

SELECT
  'PART' as entity,
  id,
  name || ' (' || part_number || ')' as description
FROM pms_parts
WHERE quantity_on_hand > 5
  AND deleted_at IS NULL
LIMIT 1

UNION ALL

SELECT
  'WORK_ORDER' as entity,
  id,
  'WO-' || number::text || ': ' || title as description
FROM pms_work_orders
WHERE status = 'in_progress'
  AND deleted_at IS NULL
LIMIT 1;
```

---

## 🚨 If Any FAIL Checks

### Critical Failures (Must Fix Before Frontend Testing)
- CHECK 1 failures → Re-run migrations
- CHECK 3 failures → Fix orphaned records
- CHECK 4 failures → Fix enum definitions
- CHECK 8 FAIL (negative stock) → Fix data corruption
- CHECK 9 failures → Re-run migration 04

### Warning Issues (Can Proceed But Note)
- CHECK 6 warnings → Frontend will work but may be slow
- CHECK 7 warnings → Security issue, fix ASAP
- CHECK 8 warnings → Old data quality issue, not critical

---

## ✅ When ALL Checks Pass

**You are ready to proceed to frontend testing!**

See: `FRONTEND_TESTING_GUIDE.md` for next steps.

---

**END OF PRE-FLIGHT CHECKS**
