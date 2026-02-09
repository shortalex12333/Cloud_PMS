-- ============================================================================
-- MIGRATION 011: Hours of Rest - RLS Policy Fixes
-- Purpose: Add missing HOD/CAPTAIN policies for cross-user access
-- Date: 2026-02-06
-- ============================================================================
-- ISSUE: Current RLS only allows users to see their own records
-- FIX: Add policies for HOD (department) and CAPTAIN (all) access
-- ============================================================================

BEGIN;

-- ============================================================================
-- Helper Functions (if not already exist)
-- ============================================================================

-- Check if functions exist
DO $$
BEGIN
    -- is_hod() function
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'is_hod') THEN
        CREATE OR REPLACE FUNCTION is_hod()
        RETURNS BOOLEAN AS $func$
        BEGIN
            RETURN EXISTS (
                SELECT 1
                FROM auth_users_profiles
                WHERE id = auth.uid()
                  AND metadata->>'role' IN ('HOD', 'CHIEF_ENGINEER', 'HOD_ENGINEERING', 'HOD_DECK')
            );
        END;
        $func$ LANGUAGE plpgsql SECURITY DEFINER;
    END IF;

    -- is_captain() function
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'is_captain') THEN
        CREATE OR REPLACE FUNCTION is_captain()
        RETURNS BOOLEAN AS $func$
        BEGIN
            RETURN EXISTS (
                SELECT 1
                FROM auth_users_profiles
                WHERE id = auth.uid()
                  AND metadata->>'role' IN ('CAPTAIN', 'MASTER')
            );
        END;
        $func$ LANGUAGE plpgsql SECURITY DEFINER;
    END IF;

    -- get_user_department() function
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'get_user_department') THEN
        CREATE OR REPLACE FUNCTION get_user_department(p_user_id UUID)
        RETURNS TEXT AS $func$
        BEGIN
            RETURN (
                SELECT metadata->>'department'
                FROM auth_users_profiles
                WHERE id = p_user_id
                LIMIT 1
            );
        END;
        $func$ LANGUAGE plpgsql SECURITY DEFINER;
    END IF;
END $$;

-- ============================================================================
-- FIX: pms_hours_of_rest - Add HOD/CAPTAIN SELECT policies
-- ============================================================================

-- Drop existing restrictive policy if it exists
DROP POLICY IF EXISTS "pms_hor_user_own_records" ON pms_hours_of_rest;

-- Recreate with proper SELECT/UPDATE split
CREATE POLICY "pms_hor_user_own_records_select" ON pms_hours_of_rest
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "pms_hor_user_own_records_update" ON pms_hours_of_rest
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- HOD can view department records
CREATE POLICY "pms_hor_hod_view_department" ON pms_hours_of_rest
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- CAPTAIN can view all records
CREATE POLICY "pms_hor_captain_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_captain());

-- ============================================================================
-- FIX: pms_crew_hours_warnings - Add HOD/CAPTAIN policies
-- ============================================================================

-- Current policy is too restrictive - HOD/CAPTAIN need to see warnings

-- HOD can view department warnings
CREATE POLICY "pms_crew_warnings_hod_view" ON pms_crew_hours_warnings
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- CAPTAIN can view all warnings
CREATE POLICY "pms_crew_warnings_captain_view" ON pms_crew_hours_warnings
    FOR SELECT
    USING (is_captain());

-- HOD/CAPTAIN can dismiss warnings (existing restrictive INSERT policy blocks auto-creation, keep it)
DROP POLICY IF EXISTS "pms_crew_hours_warnings_update" ON pms_crew_hours_warnings;

CREATE POLICY "pms_crew_hours_warnings_update" ON pms_crew_hours_warnings
    FOR UPDATE
    USING (
        (user_id = auth.uid()) OR  -- Own warnings
        (is_hod() AND get_user_department(user_id) = get_user_department(auth.uid())) OR  -- Department
        is_captain()  -- All warnings
    )
    WITH CHECK (
        -- Crew can only acknowledge (not dismiss)
        ((user_id = auth.uid()) AND (is_dismissed = false) AND (dismissed_at IS NULL)) OR
        -- HOD/CAPTAIN can dismiss
        is_hod() OR
        is_captain()
    );

-- ============================================================================
-- FIX: pms_crew_normal_hours - Templates should be user-scoped
-- ============================================================================

-- Already has good RLS, but ensure HOD/CAPTAIN can view department templates
CREATE POLICY "pms_crew_templates_hod_view" ON pms_crew_normal_hours
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_crew_templates_captain_view" ON pms_crew_normal_hours
    FOR SELECT
    USING (is_captain());

-- ============================================================================
-- GRANT PERMISSIONS (ensure functions are accessible)
-- ============================================================================

GRANT EXECUTE ON FUNCTION is_hod() TO authenticated;
GRANT EXECUTE ON FUNCTION is_captain() TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_department(UUID) TO authenticated;

-- ============================================================================
-- VERIFY POLICIES
-- ============================================================================

-- List all policies for verification
DO $$
DECLARE
    v_policy RECORD;
BEGIN
    RAISE NOTICE '=== HOR RLS Policies ===';

    FOR v_policy IN
        SELECT schemaname, tablename, policyname, permissive
        FROM pg_policies
        WHERE tablename IN ('pms_hours_of_rest', 'pms_crew_hours_warnings', 'pms_crew_normal_hours', 'pms_hor_monthly_signoffs')
        ORDER BY tablename, policyname
    LOOP
        RAISE NOTICE '% - %: %', v_policy.tablename, v_policy.policyname, v_policy.permissive;
    END LOOP;
END $$;

COMMIT;

-- ============================================================================
-- TESTING QUERIES
-- ============================================================================

-- Test 1: CREW should see own records only
-- SET app.current_yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
-- SET ROLE authenticated;
-- SET request.jwt.claim.sub = 'b72c35ff-e309-4a19-a617-bfc706a78c0f';  -- Captain Test
-- SELECT COUNT(*) FROM pms_hours_of_rest;  -- Should see own records

-- Test 2: HOD should see department records
-- SET request.jwt.claim.sub = '89b1262c-ff59-4591-b954-757cdf3d609d';  -- Chief Engineer (HOD)
-- SELECT COUNT(*) FROM pms_hours_of_rest;  -- Should see engineering dept

-- Test 3: CAPTAIN should see all records
-- SET request.jwt.claim.sub = 'b72c35ff-e309-4a19-a617-bfc706a78c0f';  -- Captain
-- SELECT COUNT(*) FROM pms_hours_of_rest;  -- Should see all 213 records
