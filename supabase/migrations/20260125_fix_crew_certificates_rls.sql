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

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_crew_certificates') THEN
        RAISE NOTICE 'pms_crew_certificates table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS
    EXECUTE 'ALTER TABLE pms_crew_certificates ENABLE ROW LEVEL SECURITY';

    -- Drop existing policies if re-running
    EXECUTE 'DROP POLICY IF EXISTS "officers_insert_crew_certificates" ON pms_crew_certificates';
    EXECUTE 'DROP POLICY IF EXISTS "officers_update_crew_certificates" ON pms_crew_certificates';
    EXECUTE 'DROP POLICY IF EXISTS "managers_delete_crew_certificates" ON pms_crew_certificates';

    -- Create INSERT policy for officers
    EXECUTE 'CREATE POLICY "officers_insert_crew_certificates" ON pms_crew_certificates
        FOR INSERT TO authenticated
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- Create UPDATE policy for officers
    EXECUTE 'CREATE POLICY "officers_update_crew_certificates" ON pms_crew_certificates
        FOR UPDATE TO authenticated
        USING (yacht_id = public.get_user_yacht_id())
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- Create DELETE policy for managers
    EXECUTE 'CREATE POLICY "managers_delete_crew_certificates" ON pms_crew_certificates
        FOR DELETE TO authenticated
        USING (
            yacht_id = public.get_user_yacht_id()
            AND is_manager(auth.uid(), public.get_user_yacht_id())
        )';

    RAISE NOTICE 'SUCCESS: pms_crew_certificates RLS enabled with policies';
END $$;
