-- ============================================================================
-- MIGRATION: 20260128_113_doc_metadata_receiving_rls.sql
-- PURPOSE: Verify doc_metadata RLS policies exist for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- REQUIRED POLICIES:
--   - crew_insert_doc_metadata (INSERT for authenticated, yacht-scoped)
--   - hod_update_doc_metadata (UPDATE for HOD, yacht-scoped)
--   - manager_delete_doc_metadata (DELETE for manager only)
-- NOTE: These should already exist from Certificate Lens v2
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
    rls_enabled BOOLEAN;
BEGIN
    -- Check if doc_metadata table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'doc_metadata'
          AND table_schema = 'public'
    ) THEN
        RAISE WARNING 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Verify RLS is enabled
    SELECT relrowsecurity INTO rls_enabled
    FROM pg_class
    WHERE relname = 'doc_metadata'
      AND relnamespace = 'public'::regnamespace;

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'BLOCKER: RLS not enabled on doc_metadata table';
    END IF;

    -- Check required policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'doc_metadata'
      AND policyname IN (
          'crew_insert_doc_metadata',
          'hod_update_doc_metadata',
          'manager_delete_doc_metadata'
      );

    IF policy_count < 3 THEN
        RAISE WARNING 'BLOCKER: Missing doc_metadata policies (found % of 3). Run 202601251012_doc_metadata_write_rls.sql', policy_count;
        RAISE EXCEPTION 'doc_metadata policies missing - Receiving Lens requires these for document linkage';
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata RLS verified (RLS enabled, % policies found)', policy_count;
    RAISE NOTICE '  - Receiving Lens can link documents via attach_receiving_image_with_comment';
END $$;
