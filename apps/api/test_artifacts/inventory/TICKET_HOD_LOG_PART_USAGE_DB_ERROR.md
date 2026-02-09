# Ticket: Fix HOD log_part_usage DB Error (org_id)

**Priority**: HIGH
**Component**: Backend / Database
**Estimated Effort**: 2 hours
**Blocking**: Inventory Lens MUTATE actions for all elevated roles

---

## 🎯 Goal

Make `log_part_usage` succeed for authorized roles (engineer, eto, chief_engineer, chief_officer, captain, manager) while preserving RLS, audit trail, and error mapping.

---

## 🔥 Problem Statement

**Current Behavior**:
HOD (chief_engineer) executing `log_part_usage` returns HTTP 400 with database error:
```json
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "Failed to log part usage: {'code': '42703', 'details': None, 'hint': None, 'message': 'record \"new\" has no field \"org_id\"'}"
}
```

**Expected Behavior**:
- HOD → HTTP 200 with `{"status": "success", ...}`
- Audit signature written: `{}`
- Part quantity decremented correctly

**Impact**:
- ❌ All elevated roles cannot log part usage
- ❌ No inventory tracking for consumed parts
- ❌ Critical workflow blocked

---

## 🔍 Root Cause

**Likely Cause**: BEFORE INSERT trigger on `pms_part_usage` table (or `deduct_part_inventory` RPC) references `NEW.org_id` field, but:
- Multi-tenant schema uses `yacht_id` as tenant key
- Table `pms_part_usage` has no `org_id` column
- Trigger/RPC tries to access non-existent field → PostgreSQL error 42703

---

## 🧪 Verification Steps

### Step 1: Inspect Table Schema
```sql
-- Check columns in pms_part_usage
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pms_part_usage'
ORDER BY ordinal_position;

-- Expected: yacht_id exists, org_id does NOT exist
```

### Step 2: Inspect Triggers
```sql
-- Find triggers on pms_part_usage
SELECT
  tgname AS trigger_name,
  tgfoid::regprocedure AS trigger_function,
  tgenabled AS enabled,
  tgtype AS trigger_type
FROM pg_trigger
WHERE tgrelid = 'pms_part_usage'::regclass
  AND NOT tgisinternal
ORDER BY tgname;

-- Example output:
-- trigger_name: pms_part_usage_before_insert
-- trigger_function: public.pms_part_usage_bi()
```

### Step 3: Inspect Trigger Function
```sql
-- Show function definition
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'pms_part_usage_bi';  -- Replace with actual function name

-- Look for: NEW.org_id references
```

### Step 4: Inspect RPC (if used)
```sql
-- Check if deduct_part_inventory RPC exists
SELECT
  proname AS function_name,
  pg_get_function_arguments(oid) AS arguments,
  pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE proname = 'deduct_part_inventory';

-- Look for: org_id parameter or NEW.org_id references
```

---

## 🔧 Remediation Options

### Option A: Remove org_id from Trigger (RECOMMENDED)

**Why**: Minimal change, safe-by-default, maintains yacht_id as single tenant key

**Steps**:

1. **Update Trigger Function** (if org_id in trigger):
```sql
-- Example: Update BEFORE INSERT trigger to use yacht_id only
CREATE OR REPLACE FUNCTION public.pms_part_usage_bi()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Validate yacht_id is present
  IF NEW.yacht_id IS NULL THEN
    RAISE EXCEPTION 'yacht_id is required';
  END IF;

  -- Set audit fields (remove any org_id references)
  NEW.created_at := COALESCE(NEW.created_at, NOW());
  NEW.used_at := COALESCE(NEW.used_at, NOW());

  -- Any derived fields computed from NEW.yacht_id here
  -- (DO NOT reference NEW.org_id)

  RETURN NEW;
END;
$$;

-- Verify trigger is attached
DROP TRIGGER IF EXISTS pms_part_usage_before_insert ON pms_part_usage;
CREATE TRIGGER pms_part_usage_before_insert
  BEFORE INSERT ON pms_part_usage
  FOR EACH ROW
  EXECUTE FUNCTION pms_part_usage_bi();
```

2. **Update RPC** (if org_id in RPC):
```sql
-- Example: Update deduct_part_inventory to use yacht_id only
CREATE OR REPLACE FUNCTION public.deduct_part_inventory(
  p_yacht_id uuid,
  p_part_id uuid,
  p_quantity integer,
  p_usage_reason text,
  p_notes text DEFAULT NULL,
  p_used_by uuid DEFAULT NULL  -- User ID from auth context
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_current_stock integer;
  v_usage_id uuid;
BEGIN
  -- 1. Validate stock availability
  SELECT quantity_on_hand INTO v_current_stock
  FROM pms_parts
  WHERE id = p_part_id
    AND yacht_id = p_yacht_id;  -- Use yacht_id, not org_id

  IF v_current_stock IS NULL THEN
    RETURN json_build_object(
      'success', false,
      'error_code', 'PART_NOT_FOUND',
      'message', 'Part not found'
    );
  END IF;

  IF v_current_stock < p_quantity THEN
    RETURN json_build_object(
      'success', false,
      'error_code', 'INSUFFICIENT_STOCK',
      'message', format('Insufficient stock: %s available, %s requested', v_current_stock, p_quantity)
    );
  END IF;

  -- 2. Insert usage record
  INSERT INTO pms_part_usage (
    yacht_id,  -- NOT org_id
    part_id,
    quantity,
    usage_reason,
    notes,
    used_by,
    used_at
  ) VALUES (
    p_yacht_id,
    p_part_id,
    p_quantity,
    p_usage_reason,
    p_notes,
    COALESCE(p_used_by, auth.uid()),
    NOW()
  )
  RETURNING id INTO v_usage_id;

  -- 3. Decrement stock
  UPDATE pms_parts
  SET
    quantity_on_hand = quantity_on_hand - p_quantity,
    last_updated_at = NOW()
  WHERE id = p_part_id
    AND yacht_id = p_yacht_id;  -- Use yacht_id, not org_id

  -- 4. Write audit log (signature = {} for non-SIGNED actions)
  INSERT INTO pms_audit_log (
    yacht_id,  -- NOT org_id
    action_type,
    entity_type,
    entity_id,
    user_id,
    signature,
    metadata
  ) VALUES (
    p_yacht_id,
    'log_part_usage',
    'part',
    p_part_id,
    COALESCE(p_used_by, auth.uid()),
    '{}'::jsonb,  -- Empty signature for MUTATE actions
    json_build_object(
      'usage_id', v_usage_id,
      'quantity', p_quantity,
      'reason', p_usage_reason
    )::jsonb
  );

  -- 5. Return success
  RETURN json_build_object(
    'success', true,
    'usage_id', v_usage_id,
    'new_stock', v_current_stock - p_quantity
  );
END;
$$;
```

3. **Review RLS Policies**:
```sql
-- Ensure RLS allows elevated roles to INSERT/UPDATE
-- pms_part_usage policy
DROP POLICY IF EXISTS "pms_part_usage_insert_elevated_roles" ON pms_part_usage;
CREATE POLICY "pms_part_usage_insert_elevated_roles"
  ON pms_part_usage
  FOR INSERT
  WITH CHECK (
    yacht_id = auth.jwt() ->> 'yacht_id'
    AND EXISTS (
      SELECT 1 FROM auth.users
      WHERE id = auth.uid()
      AND raw_user_meta_data->>'role' IN (
        'engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager'
      )
    )
  );

-- pms_parts policy (for UPDATE)
DROP POLICY IF EXISTS "pms_parts_update_elevated_roles" ON pms_parts;
CREATE POLICY "pms_parts_update_elevated_roles"
  ON pms_parts
  FOR UPDATE
  USING (
    yacht_id = auth.jwt() ->> 'yacht_id'
    AND EXISTS (
      SELECT 1 FROM auth.users
      WHERE id = auth.uid()
      AND raw_user_meta_data->>'role' IN (
        'engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager'
      )
    )
  );
```

---

### Option B: Add org_id Column (NOT RECOMMENDED)

**Why NOT**: Introduces second tenant key, increases complexity, requires backfill

**Steps** (if absolutely necessary):
```sql
-- 1. Add column
ALTER TABLE pms_part_usage ADD COLUMN org_id uuid NULL;

-- 2. Backfill from yacht→org mapping
UPDATE pms_part_usage pu
SET org_id = y.org_id
FROM yachts y
WHERE pu.yacht_id = y.id;

-- 3. Add NOT NULL constraint (after backfill)
ALTER TABLE pms_part_usage ALTER COLUMN org_id SET NOT NULL;

-- 4. Update indexes
CREATE INDEX idx_pms_part_usage_org_yacht ON pms_part_usage(org_id, yacht_id);

-- 5. Update RLS policies to include org_id checks
-- (Significant complexity increase)
```

**Recommendation**: Do NOT pursue Option B unless yacht_id alone is insufficient for tenant isolation.

---

## ✅ Acceptance Tests

After deploying fix, verify:

### Test 1: HOD log_part_usage Success
```bash
curl -s -w "\nHTTP:%{http_code}\n" \
  -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "log_part_usage",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_id": "f7913ad1-6832-4169-b816-4538c8b7a417",
      "quantity": 1,
      "usage_reason": "maintenance",
      "notes": "Test after fix"
    }
  }'

# Expected:
# {"status":"success","action":"log_part_usage","result":{...}}
# HTTP:200
```

### Test 2: CREW Still Denied
```bash
curl -s -w "\nHTTP:%{http_code}\n" \
  -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "log_part_usage",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_id": "f7913ad1-6832-4169-b816-4538c8b7a417",
      "quantity": 1
    }
  }'

# Expected:
# {"status":"error","error_code":"FORBIDDEN",...}
# HTTP:403
```

### Test 3: Insufficient Stock
```bash
# Query part with low stock (quantity_on_hand = 1)
curl -s -w "\nHTTP:%{http_code}\n" \
  -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "log_part_usage",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_id": "19770833-a0b7-42a1-a6a7-8d5316a1db3d",
      "quantity": 10,
      "usage_reason": "test"
    }
  }'

# Expected:
# {"status":"error","error_code":"INSUFFICIENT_STOCK",...}
# HTTP:400
```

### Test 4: Verify Audit Trail
```sql
-- Check audit log written with empty signature
SELECT
  action_type,
  entity_type,
  entity_id,
  signature,
  metadata
FROM pms_audit_log
WHERE action_type = 'log_part_usage'
ORDER BY created_at DESC
LIMIT 5;

-- Expected: signature = {}
```

### Test 5: Verify Stock Decremented
```sql
-- Check part quantity decreased
SELECT
  id,
  name,
  part_number,
  quantity_on_hand
FROM pms_parts
WHERE id = 'f7913ad1-6832-4169-b816-4538c8b7a417';

-- Expected: quantity_on_hand decreased by amount used
```

---

## 📁 Migration File Template

Create: `supabase/migrations/20260209_fix_part_usage_org_id.sql`

```sql
-- Migration: Fix log_part_usage org_id error
-- Date: 2026-02-09
-- Description: Remove org_id references from pms_part_usage trigger/RPC

-- 1. Update trigger function (if exists)
CREATE OR REPLACE FUNCTION public.pms_part_usage_bi()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  IF NEW.yacht_id IS NULL THEN
    RAISE EXCEPTION 'yacht_id is required';
  END IF;

  NEW.created_at := COALESCE(NEW.created_at, NOW());
  NEW.used_at := COALESCE(NEW.used_at, NOW());

  RETURN NEW;
END;
$$;

-- 2. Recreate trigger
DROP TRIGGER IF EXISTS pms_part_usage_before_insert ON pms_part_usage;
CREATE TRIGGER pms_part_usage_before_insert
  BEFORE INSERT ON pms_part_usage
  FOR EACH ROW
  EXECUTE FUNCTION pms_part_usage_bi();

-- 3. Update RPC (if exists) - see full RPC definition above

-- 4. Verify RLS policies
-- (Add policies from Option A Step 3 if missing)

-- ROLLBACK PLAN:
-- If this migration causes issues, revert by:
-- 1. Restoring previous trigger function definition
-- 2. Restoring previous RPC definition
-- 3. Rolling back RLS policy changes
```

---

## 🔗 Related Evidence

**Test Evidence**:
- `apps/api/test_artifacts/inventory/execution_sanity/hod_log_part_usage.txt`
- Shows: HTTP 400 with org_id error

**Live Test Details**:
- `apps/api/test_artifacts/inventory/finish_line/FINAL_EVIDENCE.md` (Test #5)
- `apps/api/test_artifacts/inventory/GAP_ANALYSIS.md` (Gap #3)

**Fresh JWTs**:
- `test-jwts.json` - HOD and CREW tokens for testing

---

## 📋 Checklist

- [ ] Inspect `pms_part_usage` table schema (confirm no org_id column)
- [ ] Inspect triggers on `pms_part_usage` (find org_id references)
- [ ] Inspect `deduct_part_inventory` RPC (find org_id references)
- [ ] Create migration file removing org_id dependencies
- [ ] Review/update RLS policies for elevated roles
- [ ] Test migration on staging database
- [ ] Run Test 1-5 (acceptance tests above)
- [ ] Verify audit trail writes correctly
- [ ] Deploy to production
- [ ] Run smoke tests with real user accounts

---

**Status**: Ready for Backend Engineer
**Effort**: 2 hours (1h investigation + 1h fix + testing)
**Risk**: LOW (removing unused field references)
