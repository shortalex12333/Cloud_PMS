-- ============================================================================
-- MIGRATION: Add RLS Policies to pms_vessel_certificates
-- ============================================================================
-- PROBLEM: pms_vessel_certificates has NO RLS policies
-- SOLUTION: Enable RLS and add proper yacht-scoped policies with role checks
-- SEVERITY: P0 - CRITICAL Security Fix
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_vessel_certificates') THEN
        RAISE NOTICE 'pms_vessel_certificates table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS
    EXECUTE 'ALTER TABLE pms_vessel_certificates ENABLE ROW LEVEL SECURITY';

    -- SELECT policy
    EXECUTE 'CREATE POLICY "crew_select_own_yacht_vessel_certs"
        ON pms_vessel_certificates
        FOR SELECT TO authenticated
        USING (yacht_id = public.get_user_yacht_id())';

    -- INSERT policy
    EXECUTE 'CREATE POLICY "hod_insert_vessel_certs"
        ON pms_vessel_certificates
        FOR INSERT TO authenticated
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- UPDATE policy
    EXECUTE 'CREATE POLICY "hod_update_vessel_certs"
        ON pms_vessel_certificates
        FOR UPDATE TO authenticated
        USING (yacht_id = public.get_user_yacht_id())
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- DELETE policy
    EXECUTE 'CREATE POLICY "manager_delete_vessel_certs"
        ON pms_vessel_certificates
        FOR DELETE TO authenticated
        USING (
            yacht_id = public.get_user_yacht_id()
            AND is_manager(auth.uid(), public.get_user_yacht_id())
        )';

    RAISE NOTICE 'SUCCESS: pms_vessel_certificates RLS configured';
END $$;
