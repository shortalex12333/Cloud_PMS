-- ============================================================================
-- MIGRATION: Fix pms_crew_certificates RLS (Enable + Missing INSERT/UPDATE/DELETE)
-- ============================================================================
-- PROBLEM: pms_crew_certificates may not have RLS enabled, and only has SELECT policy.
--          Officers cannot create or update crew certificates.
-- SOLUTION: Enable RLS and add INSERT/UPDATE/DELETE policies for officers
-- SEVERITY: MEDIUM - Functionality gap for crew certificate management
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Enable Row Level Security (idempotent)
-- =============================================================================
ALTER TABLE pms_crew_certificates ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 2: DROP existing policies if re-running (idempotent)
-- =============================================================================
DROP POLICY IF EXISTS "officers_insert_crew_certificates" ON pms_crew_certificates;
DROP POLICY IF EXISTS "officers_update_crew_certificates" ON pms_crew_certificates;
DROP POLICY IF EXISTS "managers_delete_crew_certificates" ON pms_crew_certificates;

-- =============================================================================
-- STEP 3: Create INSERT policy for officers (using boolean helper)
-- =============================================================================
CREATE POLICY "officers_insert_crew_certificates" ON pms_crew_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- =============================================================================
-- STEP 4: Create UPDATE policy for officers (using boolean helper)
-- =============================================================================
CREATE POLICY "officers_update_crew_certificates" ON pms_crew_certificates
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- =============================================================================
-- STEP 5: Create DELETE policy for managers
-- =============================================================================
CREATE POLICY "managers_delete_crew_certificates" ON pms_crew_certificates
    FOR DELETE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND is_manager()
    );

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
    WHERE relname = 'pms_crew_certificates';

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'RLS not enabled on pms_crew_certificates';
    END IF;

    -- Check policy count (should have SELECT + INSERT + UPDATE + DELETE = 4 minimum)
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_crew_certificates';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Expected at least 4 policies on pms_crew_certificates, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_crew_certificates RLS enabled with % policies', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "officers_insert_crew_certificates" ON pms_crew_certificates;
-- DROP POLICY IF EXISTS "officers_update_crew_certificates" ON pms_crew_certificates;
-- DROP POLICY IF EXISTS "managers_delete_crew_certificates" ON pms_crew_certificates;
-- -- Note: Do NOT disable RLS if SELECT policy still exists
-- COMMIT;
