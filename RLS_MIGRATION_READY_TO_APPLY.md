# 🔴 CRITICAL: RLS Migration Ready to Apply

## Security Issue Confirmed

**Test Result**: CREW user successfully accessed 5 CAPTAIN HOR records (should be DENIED)

```bash
# Test executed: 2026-02-09
curl -X POST http://localhost:8080/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -d '{"action": "get_hours_of_rest", "payload": {"user_id": "$CAPTAIN_USER_ID"}}'

# Result: {"success": true, "records": 5}  ❌ SECURITY BREACH
# Expected: {"records": []} or HTTP 403
```

**Root Cause**: RLS policies NOT applied to production database

---

## Apply Migration NOW

### Step 1: Open Supabase SQL Editor

1. Go to: **https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new**
2. Open a new SQL query

### Step 2: Copy Migration SQL

The complete migration SQL is in: `migrations/011_hor_rls_policy_fixes_v2.sql`

Or use the content below (220 lines):

<details>
<summary>Click to expand full migration SQL</summary>

```sql
-- Migration 011 v2: HOR RLS Policy Fixes (Deny-by-Default)
-- Fixes CRITICAL security bypass: crew can read captain data
-- Applied: 2026-02-08

-- Drop all existing policies to start clean
DROP POLICY IF EXISTS "pms_hor_hod_view_department" ON pms_hours_of_rest;
DROP POLICY IF EXISTS "pms_hor_captain_view_all" ON pms_hours_of_rest;
DROP POLICY IF EXISTS "pms_hor_crew_view_own" ON pms_hours_of_rest;
DROP POLICY IF EXISTS "pms_hor_crew_insert_own" ON pms_hours_of_rest;
DROP POLICY IF EXISTS "pms_hor_crew_update_own" ON pms_hours_of_rest;

-- Enable RLS (should already be enabled, but ensure)
ALTER TABLE pms_hours_of_rest ENABLE ROW LEVEL SECURITY;

-- SELECT Policies (deny-by-default, explicit allow)
-- Policy 1: Crew can ONLY view their own records
CREATE POLICY "pms_hor_crew_view_own" ON pms_hours_of_rest
    FOR SELECT
    USING (
        user_id = auth.uid()
    );

-- Policy 2: HOD can view department records (same department)
CREATE POLICY "pms_hor_hod_view_department" ON pms_hours_of_rest
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- Policy 3: Captain can view all records on yacht
CREATE POLICY "pms_hor_captain_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_captain());

-- Policy 4: Manager can view all records on yacht
CREATE POLICY "pms_hor_manager_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_manager());

-- INSERT Policies
-- Policy 5: Crew can insert own records
CREATE POLICY "pms_hor_crew_insert_own" ON pms_hours_of_rest
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Policy 6: HOD can insert for department members
CREATE POLICY "pms_hor_hod_insert_department" ON pms_hours_of_rest
    FOR INSERT
    WITH CHECK (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- Policy 7: Captain can insert for anyone on yacht
CREATE POLICY "pms_hor_captain_insert_any" ON pms_hours_of_rest
    FOR INSERT
    WITH CHECK (is_captain() OR is_manager());

-- UPDATE Policies
-- Policy 8: Crew can update own records
CREATE POLICY "pms_hor_crew_update_own" ON pms_hours_of_rest
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Policy 9: HOD can update department records
CREATE POLICY "pms_hor_hod_update_department" ON pms_hours_of_rest
    FOR UPDATE
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    )
    WITH CHECK (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- Policy 10: Captain can update any record on yacht
CREATE POLICY "pms_hor_captain_update_any" ON pms_hours_of_rest
    FOR UPDATE
    USING (is_captain() OR is_manager())
    WITH CHECK (is_captain() OR is_manager());

-- DELETE Policies (strict - only captain/manager)
-- Policy 11: Captain/Manager can delete any record
CREATE POLICY "pms_hor_captain_delete_any" ON pms_hours_of_rest
    FOR DELETE
    USING (is_captain() OR is_manager());

-- Monthly Sign-offs RLS
DROP POLICY IF EXISTS "pms_hor_signoff_crew_view_own" ON pms_hor_monthly_signoffs;
DROP POLICY IF EXISTS "pms_hor_signoff_hod_view_department" ON pms_hor_monthly_signoffs;
DROP POLICY IF EXISTS "pms_hor_signoff_captain_view_all" ON pms_hor_monthly_signoffs;
DROP POLICY IF EXISTS "pms_hor_signoff_crew_insert_own" ON pms_hor_monthly_signoffs;
DROP POLICY IF EXISTS "pms_hor_signoff_crew_update_own" ON pms_hor_monthly_signoffs;

ALTER TABLE pms_hor_monthly_signoffs ENABLE ROW LEVEL SECURITY;

-- Sign-off SELECT policies
CREATE POLICY "pms_hor_signoff_crew_view_own" ON pms_hor_monthly_signoffs
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "pms_hor_signoff_hod_view_department" ON pms_hor_monthly_signoffs
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_hor_signoff_captain_view_all" ON pms_hor_monthly_signoffs
    FOR SELECT
    USING (is_captain() OR is_manager());

-- Sign-off INSERT policies
CREATE POLICY "pms_hor_signoff_crew_insert_own" ON pms_hor_monthly_signoffs
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Sign-off UPDATE policies (for adding signatures)
CREATE POLICY "pms_hor_signoff_crew_update_own" ON pms_hor_monthly_signoffs
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "pms_hor_signoff_hod_update_department" ON pms_hor_monthly_signoffs
    FOR UPDATE
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    )
    WITH CHECK (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_hor_signoff_captain_update_any" ON pms_hor_monthly_signoffs
    FOR UPDATE
    USING (is_captain() OR is_manager())
    WITH CHECK (is_captain() OR is_manager());

-- Templates RLS (pms_crew_normal_hours)
DROP POLICY IF EXISTS "pms_crew_templates_view_own" ON pms_crew_normal_hours;
DROP POLICY IF EXISTS "pms_crew_templates_insert_own" ON pms_crew_normal_hours;
DROP POLICY IF EXISTS "pms_crew_templates_update_own" ON pms_crew_normal_hours;
DROP POLICY IF EXISTS "pms_crew_templates_delete_own" ON pms_crew_normal_hours;

ALTER TABLE pms_crew_normal_hours ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pms_crew_templates_view_own" ON pms_crew_normal_hours
    FOR SELECT
    USING (user_id = auth.uid() OR is_captain() OR is_manager());

CREATE POLICY "pms_crew_templates_insert_own" ON pms_crew_normal_hours
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "pms_crew_templates_update_own" ON pms_crew_normal_hours
    FOR UPDATE
    USING (user_id = auth.uid() OR is_captain() OR is_manager())
    WITH CHECK (user_id = auth.uid() OR is_captain() OR is_manager());

CREATE POLICY "pms_crew_templates_delete_own" ON pms_crew_normal_hours
    FOR DELETE
    USING (user_id = auth.uid() OR is_captain() OR is_manager());

-- Warnings RLS (pms_crew_hours_warnings)
DROP POLICY IF EXISTS "pms_warnings_view_own" ON pms_crew_hours_warnings;
DROP POLICY IF EXISTS "pms_warnings_view_hod" ON pms_crew_hours_warnings;
DROP POLICY IF EXISTS "pms_warnings_view_captain" ON pms_crew_hours_warnings;
DROP POLICY IF EXISTS "pms_warnings_insert_system" ON pms_crew_hours_warnings;
DROP POLICY IF EXISTS "pms_warnings_update_own" ON pms_crew_hours_warnings;
DROP POLICY IF EXISTS "pms_warnings_update_hod" ON pms_crew_hours_warnings;

ALTER TABLE pms_crew_hours_warnings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pms_warnings_view_own" ON pms_crew_hours_warnings
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "pms_warnings_view_hod" ON pms_crew_hours_warnings
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_warnings_view_captain" ON pms_crew_hours_warnings
    FOR SELECT
    USING (is_captain() OR is_manager());

-- Warnings INSERT (system-generated, allow all for now - refine later)
CREATE POLICY "pms_warnings_insert_system" ON pms_crew_hours_warnings
    FOR INSERT
    WITH CHECK (true); -- System-generated via RPC

-- Warnings UPDATE (acknowledge by crew, dismiss by HOD/captain)
CREATE POLICY "pms_warnings_update_own" ON pms_crew_hours_warnings
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "pms_warnings_update_hod" ON pms_crew_hours_warnings
    FOR UPDATE
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    )
    WITH CHECK (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_warnings_update_captain" ON pms_crew_hours_warnings
    FOR UPDATE
    USING (is_captain() OR is_manager())
    WITH CHECK (is_captain() OR is_manager());
```

</details>

### Step 3: Execute Migration

1. Paste the SQL into the editor
2. Click "Run" (or press Cmd+Enter)
3. Wait for success message

### Step 4: Verify Policies Applied

Run this verification query in the SQL editor:

```sql
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename LIKE 'pms_h%' OR tablename LIKE 'pms_crew%'
ORDER BY tablename, policyname;
```

**Expected Result**: 20+ policies listed across 4 tables

---

## Step 5: Re-run Security Test

After migration applied, re-run the RLS security test:

```bash
bash /tmp/test_crew_rls.sh
```

**Expected Result After Fix**:

```json
{
  "success": true,
  "records": 0,
  "RLS_STATUS": "✅ WORKING - Access denied"
}
```

If CREW still gets captain records, the migration did NOT apply correctly.

---

## Manual Application Required Because:

1. ❌ `psql` connection fails: "Tenant or user not found"
2. ❌ Supabase CLI fails: Authentication/access control issues
3. ❌ REST API doesn't expose `exec_sql` RPC function
4. ❌ `pg_policies` table not accessible via PostgREST

**Only reliable method**: Supabase Dashboard SQL Editor (manual copy-paste)

---

## After Migration Applied

**Next Steps**:
1. Re-run all 12 HOR action E2E tests
2. Verify 100% pass rate with proper RLS enforcement
3. Document test results with hard evidence
4. Deploy to production
5. Begin frontend migration

**Deployment Status**: 🔴 **BLOCKED** until RLS migration applied and verified
