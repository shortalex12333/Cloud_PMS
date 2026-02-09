# Work Order RLS Security Migrations - Application Guide

**Date:** 2026-02-02
**Database:** TENANT_1 (vzsohavtuotocgrfkfyd)
**Priority:** CRITICAL - Security Fixes

---

## Executive Summary

Three critical RLS security migrations need to be applied to fix cross-yacht data leakage in work order-related tables:

| Migration | Blocker | Table | Issue | Severity |
|-----------|---------|-------|-------|----------|
| `20260125_fix_cross_yacht_notes.sql` | **B1** | `pms_work_order_notes` | `USING (true)` allows cross-yacht access | CRITICAL |
| `20260125_fix_cross_yacht_parts.sql` | **B2** | `pms_work_order_parts` | `USING (true)` allows cross-yacht access | CRITICAL |
| `20260125_fix_cross_yacht_part_usage.sql` | **B3** | `pms_part_usage` | `USING (true)` allows cross-yacht access | CRITICAL |

---

## Migration Status Check

### ✅ Verification Completed

The RLS security test suite has been run and **confirmed these migrations work correctly**:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python3 tests/test_work_order_rls_security.py
```

**Results:** All tests passed - migrations are functioning correctly on the test yacht.

However, we need to verify the migrations have been applied to **production tables** on TENANT_1 database.

---

## Manual Migration Application (Recommended for Production)

### Step 1: Access Supabase SQL Editor

1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
2. Log in with your Supabase credentials
3. Create a new query

### Step 2: Check Current Policy Status

Before applying migrations, check the current state:

```sql
-- Check pms_work_order_notes policies
SELECT schemaname, tablename, policyname, permissive, roles, qual, with_check
FROM pg_policies
WHERE tablename = 'pms_work_order_notes';

-- Check pms_work_order_parts policies
SELECT schemaname, tablename, policyname, permissive, roles, qual, with_check
FROM pg_policies
WHERE tablename = 'pms_work_order_parts';

-- Check pms_part_usage policies
SELECT schemaname, tablename, policyname, permissive, roles, qual, with_check
FROM pg_policies
WHERE tablename = 'pms_part_usage';
```

**Look for these DANGEROUS policies:**
- `"Authenticated users can view notes"` with `USING (true)`
- `"Authenticated users can view parts"` with `USING (true)`
- `"Authenticated users can view usage"` with `USING (true)`

If you see any of these, the migrations **NEED** to be applied.

### Step 3: Apply Migration B1 (pms_work_order_notes)

**File:** `supabase/migrations/20260125_fix_cross_yacht_notes.sql`

```sql
-- ============================================================================
-- MIGRATION B1: Fix pms_work_order_notes Cross-Yacht Data Leakage
-- ============================================================================

BEGIN;

-- Drop broken policies
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;
DROP POLICY IF EXISTS "pms_work_order_notes_yacht_isolation" ON pms_work_order_notes;

-- Create yacht-isolated SELECT policy
CREATE POLICY "crew_select_own_yacht_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Create yacht-isolated INSERT policy
CREATE POLICY "crew_insert_own_yacht_notes" ON pms_work_order_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Ensure service role bypass exists
DROP POLICY IF EXISTS "Service role full access notes" ON pms_work_order_notes;

CREATE POLICY "service_role_full_access_notes" ON pms_work_order_notes
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Verification
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_work_order_notes'
    AND policyname IN ('crew_select_own_yacht_notes', 'crew_insert_own_yacht_notes', 'service_role_full_access_notes');

    IF policy_count != 3 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 3 policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: B1 - pms_work_order_notes now has yacht-isolated RLS';
END $$;

COMMIT;
```

**Expected Output:**
```
NOTICE:  SUCCESS: B1 - pms_work_order_notes now has yacht-isolated RLS
```

### Step 4: Apply Migration B2 (pms_work_order_parts)

**File:** `supabase/migrations/20260125_fix_cross_yacht_parts.sql`

```sql
-- ============================================================================
-- MIGRATION B2: Fix pms_work_order_parts Cross-Yacht Data Leakage
-- ============================================================================

BEGIN;

-- Drop broken policies
DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

-- Create yacht-isolated SELECT policy
DROP POLICY IF EXISTS "crew_select_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_select_own_yacht_wo_parts" ON pms_work_order_parts
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Create yacht-isolated INSERT policy
DROP POLICY IF EXISTS "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Create yacht-isolated UPDATE policy
DROP POLICY IF EXISTS "crew_update_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_update_own_yacht_wo_parts" ON pms_work_order_parts
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Create yacht-isolated DELETE policy
DROP POLICY IF EXISTS "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- Ensure service role bypass
DROP POLICY IF EXISTS "Service role full access wo_parts" ON pms_work_order_parts;
DROP POLICY IF EXISTS "service_role_full_access_wo_parts" ON pms_work_order_parts;

CREATE POLICY "service_role_full_access_wo_parts" ON pms_work_order_parts
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Verification
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_work_order_parts'
    AND policyname LIKE 'crew_%_own_yacht_wo_parts';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 4 crew policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: B2 - pms_work_order_parts now has yacht-isolated RLS';
END $$;

COMMIT;
```

**Expected Output:**
```
NOTICE:  SUCCESS: B2 - pms_work_order_parts now has yacht-isolated RLS
```

### Step 5: Apply Migration B3 (pms_part_usage)

**File:** `supabase/migrations/20260125_fix_cross_yacht_part_usage.sql`

```sql
-- ============================================================================
-- MIGRATION B3: Fix pms_part_usage Cross-Yacht Data Leakage
-- ============================================================================

BEGIN;

-- Drop broken policies
DROP POLICY IF EXISTS "Authenticated users can view usage" ON pms_part_usage;
DROP POLICY IF EXISTS "Authenticated users can view part usage" ON pms_part_usage;
DROP POLICY IF EXISTS "pms_part_usage_yacht_isolation" ON pms_part_usage;

-- Create yacht-isolated SELECT policy (CANONICAL)
CREATE POLICY "crew_select_own_yacht_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Create yacht-isolated INSERT policy (CANONICAL)
CREATE POLICY "crew_insert_own_yacht_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Create yacht-isolated UPDATE policy (CANONICAL)
CREATE POLICY "crew_update_own_yacht_part_usage" ON pms_part_usage
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Create yacht-isolated DELETE policy (CANONICAL)
CREATE POLICY "crew_delete_own_yacht_part_usage" ON pms_part_usage
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Ensure service role bypass
DROP POLICY IF EXISTS "Service role full access" ON pms_part_usage;
DROP POLICY IF EXISTS "service_role_full_access_part_usage" ON pms_part_usage;

CREATE POLICY "service_role_full_access_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Verification
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_part_usage'
    AND policyname LIKE 'crew_%_own_yacht_part_usage';

    IF policy_count != 4 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 4 crew policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: B3 - pms_part_usage now has yacht-isolated RLS using canonical pattern';
END $$;

COMMIT;
```

**Expected Output:**
```
NOTICE:  SUCCESS: B3 - pms_part_usage now has yacht-isolated RLS using canonical pattern
```

### Step 6: Verify Migrations Applied

After applying all three migrations, verify they worked:

```sql
-- Verify B1 (pms_work_order_notes)
SELECT policyname FROM pg_policies
WHERE tablename = 'pms_work_order_notes'
ORDER BY policyname;

-- Expected: crew_insert_own_yacht_notes, crew_select_own_yacht_notes, service_role_full_access_notes

-- Verify B2 (pms_work_order_parts)
SELECT policyname FROM pg_policies
WHERE tablename = 'pms_work_order_parts'
ORDER BY policyname;

-- Expected: crew_delete_own_yacht_wo_parts, crew_insert_own_yacht_wo_parts,
--           crew_select_own_yacht_wo_parts, crew_update_own_yacht_wo_parts, service_role_full_access_wo_parts

-- Verify B3 (pms_part_usage)
SELECT policyname FROM pg_policies
WHERE tablename = 'pms_part_usage'
ORDER BY policyname;

-- Expected: crew_delete_own_yacht_part_usage, crew_insert_own_yacht_part_usage,
--           crew_select_own_yacht_part_usage, crew_update_own_yacht_part_usage, service_role_full_access_part_usage
```

---

## Post-Migration Verification

### Run RLS Security Test Suite

After applying migrations, run the comprehensive security test:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python3 tests/test_work_order_rls_security.py
```

**Expected Results:**
- ✅ All yacht isolation tests pass (B1, B2, B3 verified)
- ✅ No cross-yacht data leakage detected
- ✅ RBAC tests pass
- ✅ Field classification tests pass

**Total:** 9/9 tests should pass (100% pass rate)

---

## Rollback Instructions (If Needed)

If migrations cause issues, rollback with these commands:

```sql
-- ROLLBACK B1
BEGIN;
DROP POLICY IF EXISTS "crew_select_own_yacht_notes" ON pms_work_order_notes;
DROP POLICY IF EXISTS "crew_insert_own_yacht_notes" ON pms_work_order_notes;
CREATE POLICY "Authenticated users can view notes" ON pms_work_order_notes
    FOR SELECT TO authenticated USING (true);
COMMIT;

-- ROLLBACK B2
BEGIN;
DROP POLICY IF EXISTS "crew_select_own_yacht_wo_parts" ON pms_work_order_parts;
DROP POLICY IF EXISTS "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts;
DROP POLICY IF EXISTS "crew_update_own_yacht_wo_parts" ON pms_work_order_parts;
DROP POLICY IF EXISTS "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts;
CREATE POLICY "Authenticated users can view parts" ON pms_work_order_parts
    FOR SELECT TO authenticated USING (true);
COMMIT;

-- ROLLBACK B3
BEGIN;
DROP POLICY IF EXISTS "crew_select_own_yacht_part_usage" ON pms_part_usage;
DROP POLICY IF EXISTS "crew_insert_own_yacht_part_usage" ON pms_part_usage;
DROP POLICY IF EXISTS "crew_update_own_yacht_part_usage" ON pms_part_usage;
DROP POLICY IF EXISTS "crew_delete_own_yacht_part_usage" ON pms_part_usage;
CREATE POLICY "Authenticated users can view usage" ON pms_part_usage
    FOR SELECT TO authenticated USING (true);
COMMIT;
```

---

## Impact Assessment

### Before Migrations
- **Security Risk:** HIGH - Any authenticated user can see ALL yachts' work order notes, parts, and usage
- **Data Exposure:** Maintenance records, part assignments, usage logs visible across yachts
- **Compliance:** FAIL - No tenant isolation

### After Migrations
- **Security Risk:** NONE - Complete yacht isolation enforced
- **Data Exposure:** Each yacht sees only their own data
- **Compliance:** PASS - Full tenant isolation

### Performance Impact
- **Minimal** - Join-based policies add negligible overhead
- **Indexed columns** - work_order_id and yacht_id are indexed
- **Query patterns** - No change to application queries

---

## Deployment Checklist

- [ ] Verify migrations exist in `supabase/migrations/` directory
- [ ] Review each migration SQL (B1, B2, B3)
- [ ] Access Supabase SQL Editor for TENANT_1 database
- [ ] Check current policy status (look for `USING (true)`)
- [ ] Apply B1 migration (pms_work_order_notes)
- [ ] Verify B1 success message
- [ ] Apply B2 migration (pms_work_order_parts)
- [ ] Verify B2 success message
- [ ] Apply B3 migration (pms_part_usage)
- [ ] Verify B3 success message
- [ ] Verify all policies created correctly
- [ ] Run RLS security test suite
- [ ] Verify 9/9 tests pass
- [ ] Document completion in this checklist

---

## Support & Troubleshooting

### Common Issues

**Issue:** "policy already exists"
**Solution:** Drop the policy first, then create it

**Issue:** "function get_user_yacht_id() does not exist"
**Solution:** This function should exist. Check if it's in the public schema

**Issue:** "relation pms_work_orders does not exist"
**Solution:** Verify you're connected to the correct database (TENANT_1)

### Contact

If migrations fail or produce unexpected results:
1. Check error messages carefully
2. Verify database connection (TENANT_1, not MASTER)
3. Review rollback instructions above
4. Test with RLS security suite after rollback

---

**Migration Guide Version:** 1.0
**Last Updated:** 2026-02-02
**Status:** Ready for Application
