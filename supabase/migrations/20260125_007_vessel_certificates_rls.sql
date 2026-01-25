-- ============================================================================
-- MIGRATION: Add RLS Policies to pms_vessel_certificates
-- ============================================================================
-- PROBLEM: pms_vessel_certificates has NO RLS policies
--          This allows any authenticated user to potentially access
--          all yachts' vessel certificates (CRITICAL security gap)
-- SOLUTION: Enable RLS and add proper yacht-scoped policies with role checks
-- SEVERITY: P0 - CRITICAL Security Fix
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Enable Row Level Security
-- =============================================================================
ALTER TABLE pms_vessel_certificates ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 2: SELECT policy - All authenticated crew can view own yacht's certs
-- =============================================================================
CREATE POLICY "crew_select_own_yacht_vessel_certs"
ON pms_vessel_certificates
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 3: INSERT policy - HOD roles only (using boolean helper)
-- =============================================================================
CREATE POLICY "hod_insert_vessel_certs"
ON pms_vessel_certificates
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 4: UPDATE policy - HOD roles only (using boolean helper)
-- =============================================================================
CREATE POLICY "hod_update_vessel_certs"
ON pms_vessel_certificates
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 5: DELETE policy - Manager only (using boolean helper)
-- =============================================================================
CREATE POLICY "manager_delete_vessel_certs"
ON pms_vessel_certificates
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);

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
    WHERE relname = 'pms_vessel_certificates';

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'RLS not enabled on pms_vessel_certificates';
    END IF;

    -- Check policy count
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_vessel_certificates';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Expected at least 4 policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_vessel_certificates RLS configured with % policies', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "hod_insert_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "hod_update_vessel_certs" ON pms_vessel_certificates;
-- DROP POLICY IF EXISTS "manager_delete_vessel_certs" ON pms_vessel_certificates;
-- ALTER TABLE pms_vessel_certificates DISABLE ROW LEVEL SECURITY;
-- COMMIT;
