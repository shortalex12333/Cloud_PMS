-- ============================================================================
-- MIGRATION: 20260128_111_documents_storage_policies_receiving.sql
-- PURPOSE: Verify storage policies for 'documents' bucket (Receiving Lens v1)
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- STORAGE PATHS:
--   - PDFs: {yacht_id}/receiving/{receiving_id}/{filename}
--   - Bucket: documents
-- POLICIES:
--   - INSERT: HOD+ for yacht path
--   - UPDATE: HOD+ for yacht path
--   - DELETE: Manager only for yacht path
-- NOTE: These policies should already exist from Certificate Lens v2
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check if required storage policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname IN (
          'hod_insert_yacht_documents',
          'hod_update_yacht_documents',
          'manager_delete_yacht_documents'
      );

    IF policy_count < 3 THEN
        RAISE WARNING 'BLOCKER: Missing storage policies for documents bucket (found % of 3). Run 202601251011_documents_storage_write_policies.sql', policy_count;
        RAISE EXCEPTION 'Storage policies missing for documents bucket - Receiving Lens requires these for PDF upload';
    END IF;

    RAISE NOTICE 'SUCCESS: Storage policies verified for documents bucket (% policies found)', policy_count;
    RAISE NOTICE '  - Receiving Lens can upload PDFs to {yacht_id}/receiving/{receiving_id}/{filename}';
END $$;
