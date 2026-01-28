-- ============================================================================
-- MIGRATION: Add Write Policies to doc_metadata
-- ============================================================================
-- PROBLEM: doc_metadata may only have SELECT policy
-- SOLUTION: Add INSERT for authenticated (yacht-scoped), UPDATE for HOD
-- SEVERITY: P1 - Required for certificate document upload flow
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doc_metadata') THEN
        RAISE NOTICE 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS
    EXECUTE 'ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY';

    -- Drop existing policies if re-running
    EXECUTE 'DROP POLICY IF EXISTS "crew_insert_doc_metadata" ON doc_metadata';
    EXECUTE 'DROP POLICY IF EXISTS "hod_update_doc_metadata" ON doc_metadata';
    EXECUTE 'DROP POLICY IF EXISTS "manager_delete_doc_metadata" ON doc_metadata';

    -- INSERT policy
    EXECUTE 'CREATE POLICY "crew_insert_doc_metadata" ON doc_metadata
        FOR INSERT TO authenticated
        WITH CHECK (
            yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        )';

    -- UPDATE policy
    EXECUTE 'CREATE POLICY "hod_update_doc_metadata" ON doc_metadata
        FOR UPDATE TO authenticated
        USING (
            yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        )
        WITH CHECK (
            yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
            AND is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- DELETE policy
    EXECUTE 'CREATE POLICY "manager_delete_doc_metadata" ON doc_metadata
        FOR DELETE TO authenticated
        USING (
            yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
            AND is_manager(auth.uid(), public.get_user_yacht_id())
        )';

    RAISE NOTICE 'SUCCESS: doc_metadata write policies created';
END $$;
