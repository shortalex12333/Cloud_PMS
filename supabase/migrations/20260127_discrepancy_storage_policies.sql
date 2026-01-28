-- ============================================================================
-- MIGRATION: Add Storage Write Policies for pms-discrepancy-photos Bucket
-- ============================================================================
-- PROBLEM: Storage bucket `pms-discrepancy-photos` may lack INSERT/UPDATE/DELETE
--          policies preventing crew from uploading fault photos
-- SOLUTION: Add complete storage policies for yacht-scoped photo management
-- SEVERITY: P1 - Required for Fault Lens
-- LENS: Fault Lens v1
-- DATE: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Drop existing policies if any (to avoid conflicts)
-- =============================================================================
DROP POLICY IF EXISTS "crew_upload_discrepancy_photos" ON storage.objects;
DROP POLICY IF EXISTS "crew_read_discrepancy_photos" ON storage.objects;
DROP POLICY IF EXISTS "hod_delete_discrepancy_photos" ON storage.objects;
DROP POLICY IF EXISTS "crew_update_discrepancy_photos" ON storage.objects;

-- =============================================================================
-- STEP 2: SELECT policy - All crew can read their yacht's photos
-- =============================================================================
-- Path format: {yacht_id}/faults/{fault_id}/{filename}
-- First folder segment is yacht_id for isolation
CREATE POLICY "crew_read_discrepancy_photos"
ON storage.objects
FOR SELECT TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- =============================================================================
-- STEP 3: INSERT policy - All crew can upload photos to their yacht
-- =============================================================================
-- All crew can upload fault photos (reporting evidence)
CREATE POLICY "crew_upload_discrepancy_photos"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- =============================================================================
-- STEP 4: UPDATE policy - All crew can update metadata of their yacht's photos
-- =============================================================================
CREATE POLICY "crew_update_discrepancy_photos"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
)
WITH CHECK (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- =============================================================================
-- STEP 5: DELETE policy - HOD+ only
-- =============================================================================
-- Only HOD roles (captain, chief_engineer, etc.) can delete photos
-- This prevents accidental deletion of evidence
CREATE POLICY "hod_delete_discrepancy_photos"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 6: Verification
-- =============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check storage policies count for our bucket
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
    AND tablename = 'objects'
    AND policyname LIKE '%discrepancy%';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Expected at least 4 storage policies for discrepancy photos, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms-discrepancy-photos storage configured with % policies', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_read_discrepancy_photos" ON storage.objects;
-- DROP POLICY IF EXISTS "crew_upload_discrepancy_photos" ON storage.objects;
-- DROP POLICY IF EXISTS "crew_update_discrepancy_photos" ON storage.objects;
-- DROP POLICY IF EXISTS "hod_delete_discrepancy_photos" ON storage.objects;
-- COMMIT;
