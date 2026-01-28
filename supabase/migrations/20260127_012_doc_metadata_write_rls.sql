-- ============================================================================
-- MIGRATION: 20260127_012_doc_metadata_write_rls.sql
-- PURPOSE: RLS policies for doc_metadata table
-- LENS: Equipment Lens v2
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doc_metadata' AND table_schema = 'public') THEN
        RAISE NOTICE 'doc_metadata table does not exist - skipping';
        RETURN;
    END IF;

    -- Enable RLS
    ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;

    -- DROP existing policies for idempotency
    DROP POLICY IF EXISTS "Crew can view doc metadata" ON doc_metadata;
    DROP POLICY IF EXISTS "Crew can insert doc metadata" ON doc_metadata;
    DROP POLICY IF EXISTS "HOD can update doc metadata" ON doc_metadata;
    DROP POLICY IF EXISTS "Manager can delete doc metadata" ON doc_metadata;
    DROP POLICY IF EXISTS "Service role doc metadata bypass" ON doc_metadata;

    -- SELECT: All crew can view their yacht's doc metadata
    EXECUTE 'CREATE POLICY "Crew can view doc metadata"
        ON doc_metadata
        FOR SELECT TO authenticated
        USING (yacht_id = public.get_user_yacht_id())';

    -- INSERT: All crew can create doc metadata
    EXECUTE 'CREATE POLICY "Crew can insert doc metadata"
        ON doc_metadata
        FOR INSERT TO authenticated
        WITH CHECK (yacht_id = public.get_user_yacht_id())';

    -- UPDATE: HOD can update doc metadata
    EXECUTE 'CREATE POLICY "HOD can update doc metadata"
        ON doc_metadata
        FOR UPDATE TO authenticated
        USING (yacht_id = public.get_user_yacht_id())
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND public.is_hod(auth.uid(), public.get_user_yacht_id())
        )';

    -- DELETE: Manager only
    EXECUTE 'CREATE POLICY "Manager can delete doc metadata"
        ON doc_metadata
        FOR DELETE TO authenticated
        USING (
            yacht_id = public.get_user_yacht_id()
            AND public.is_manager()
        )';

    -- Service role bypass
    EXECUTE 'CREATE POLICY "Service role doc metadata bypass"
        ON doc_metadata
        FOR ALL TO service_role
        USING (true) WITH CHECK (true)';

    RAISE NOTICE 'SUCCESS: doc_metadata RLS policies created';
END $$;
