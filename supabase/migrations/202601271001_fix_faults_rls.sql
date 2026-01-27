-- ============================================================================
-- MIGRATION: Add Full RLS Policies to pms_faults
-- ============================================================================
-- PROBLEM: pms_faults has SELECT-only RLS (legacy policy using user_profiles)
--          This allows any authenticated user to read but not properly write
--          Need INSERT for reporting faults and UPDATE for engineers+
-- SOLUTION: Replace legacy SELECT policy and add INSERT/UPDATE policies
-- SEVERITY: P0 - CRITICAL Security Fix
-- LENS: Fault Lens v1
-- DATE: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Drop legacy SELECT policy (uses old user_profiles table reference)
-- =============================================================================
DROP POLICY IF EXISTS "Users can view their yacht faults" ON pms_faults;

-- =============================================================================
-- STEP 2: SELECT policy - All authenticated crew can view own yacht's faults
-- =============================================================================
CREATE POLICY "crew_select_own_yacht_faults"
ON pms_faults
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 3: INSERT policy - All crew can report faults
-- =============================================================================
-- Note: All crew members can report faults they observe
-- The actual fault ownership and investigation is done by engineers+
CREATE POLICY "crew_insert_faults"
ON pms_faults
FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 4: UPDATE policy - HOD + captain only
-- =============================================================================
-- Per binding brief: "HOD (chief_engineer, chief_officer) + captain: all other Fault mutations"
-- Crew can report_fault (INSERT) and add notes/photos, but NOT update faults directly
-- is_hod() covers: captain, chief_engineer, chief_officer, purser, manager
CREATE POLICY "hod_update_faults"
ON pms_faults
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 5: DELETE policy - NONE (doctrine forbids fault deletion)
-- =============================================================================
-- Faults are NEVER deleted - history is preserved for recurrence analysis
-- No DELETE policy will be created

-- =============================================================================
-- NOTE: Service role bypasses RLS automatically - no explicit policy needed
-- =============================================================================

-- =============================================================================
-- STEP 6: Verification
-- =============================================================================
DO $$
DECLARE
    rls_enabled BOOLEAN;
    policy_count INTEGER;
BEGIN
    -- Check RLS enabled
    SELECT relrowsecurity INTO rls_enabled
    FROM pg_class
    WHERE relname = 'pms_faults';

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'RLS not enabled on pms_faults';
    END IF;

    -- Check policy count (should have 3: SELECT, INSERT, UPDATE)
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_faults';

    IF policy_count < 3 THEN
        RAISE EXCEPTION 'Expected at least 3 policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_faults RLS configured with % policies', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_faults" ON pms_faults;
-- DROP POLICY IF EXISTS "crew_insert_faults" ON pms_faults;
-- DROP POLICY IF EXISTS "engineer_update_faults" ON pms_faults;
-- -- Restore legacy policy if needed:
-- CREATE POLICY "Users can view their yacht faults"
--     ON pms_faults FOR SELECT
--     USING (yacht_id IN (
--         SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
--     ));
-- COMMIT;
