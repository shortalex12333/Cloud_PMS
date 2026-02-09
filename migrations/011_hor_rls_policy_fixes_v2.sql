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

-- Verification queries
-- SELECT tablename, policyname, cmd, roles, qual FROM pg_policies WHERE tablename LIKE 'pms_h%' OR tablename LIKE 'pms_crew%' ORDER BY tablename, policyname;
