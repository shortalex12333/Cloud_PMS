-- ============================================================================
-- MIGRATION: Add Write Policies to documents Storage Bucket
-- ============================================================================
-- PROBLEM: storage.objects for 'documents' bucket only has SELECT policy
--          INSERT/UPDATE/DELETE policies missing - HOD cannot upload certificates
-- SOLUTION: Add INSERT/UPDATE for HOD, DELETE for managers
-- SEVERITY: P1 - Functionality Gap (certificates cannot be uploaded)
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: INSERT policy - HOD can upload to their yacht's path
-- =============================================================================
-- Path convention: documents/{yacht_id}/certificates/{certificate_id}/{filename}
-- storage.foldername(name) is 1-indexed, so [1] extracts yacht_id
-- =============================================================================
CREATE POLICY "hod_insert_yacht_documents"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- =============================================================================
-- STEP 2: UPDATE policy - HOD can update their yacht's files
-- =============================================================================
CREATE POLICY "hod_update_yacht_documents"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
)
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- =============================================================================
-- STEP 3: DELETE policy - Manager only can delete yacht documents
-- =============================================================================
CREATE POLICY "manager_delete_yacht_documents"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND is_manager()
);

-- =============================================================================
-- STEP 4: Verification
-- =============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check policy count for documents bucket
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'objects'
      AND schemaname = 'storage'
      AND policyname LIKE '%yacht_documents%';

    IF policy_count < 3 THEN
        RAISE EXCEPTION 'Expected at least 3 new storage policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: storage.objects write policies configured (% policies for yacht documents)', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "hod_insert_yacht_documents" ON storage.objects;
-- DROP POLICY IF EXISTS "hod_update_yacht_documents" ON storage.objects;
-- DROP POLICY IF EXISTS "manager_delete_yacht_documents" ON storage.objects;
-- COMMIT;
