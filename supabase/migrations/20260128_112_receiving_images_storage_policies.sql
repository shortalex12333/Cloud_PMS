-- ============================================================================
-- MIGRATION: 20260128_112_receiving_images_storage_policies.sql
-- PURPOSE: Create storage policies for 'pms-receiving-images' bucket
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- STORAGE PATHS:
--   - Photos: {yacht_id}/receiving/{receiving_id}/{filename}
--   - Bucket: pms-receiving-images
-- POLICIES:
--   - INSERT: HOD+ for yacht path
--   - UPDATE: HOD+ for yacht path
--   - DELETE: Manager only for yacht path
--   - SELECT: All crew for yacht path
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Ensure bucket exists (informational - buckets created via UI/API)
-- ============================================================================
-- NOTE: Buckets are created via Supabase Storage UI or API
-- This migration assumes 'pms-receiving-images' bucket exists
-- If not, handler will fail with 404 bucket error

-- ============================================================================
-- STEP 2: DROP existing policies for idempotency
-- ============================================================================
DROP POLICY IF EXISTS "hod_insert_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "hod_update_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "manager_delete_receiving_images" ON storage.objects;
DROP POLICY IF EXISTS "crew_select_receiving_images" ON storage.objects;

-- ============================================================================
-- STEP 3: SELECT policy - All crew can view their yacht's receiving images
-- ============================================================================
CREATE POLICY "crew_select_receiving_images"
ON storage.objects
FOR SELECT TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
);

-- ============================================================================
-- STEP 4: INSERT policy - HOD can upload to their yacht's receiving path
-- ============================================================================
-- Path convention: pms-receiving-images/{yacht_id}/receiving/{receiving_id}/{filename}
-- storage.foldername(name) is 1-indexed, so [1] extracts yacht_id
-- ============================================================================
CREATE POLICY "hod_insert_receiving_images"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- ============================================================================
-- STEP 5: UPDATE policy - HOD can update their yacht's receiving images
-- ============================================================================
CREATE POLICY "hod_update_receiving_images"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
)
WITH CHECK (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_hod(auth.uid(), (
        SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()
    ))
);

-- ============================================================================
-- STEP 6: DELETE policy - Manager only can delete yacht receiving images
-- ============================================================================
CREATE POLICY "manager_delete_receiving_images"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
    )
    AND public.is_manager(auth.uid(), public.get_user_yacht_id())
);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check policy count for pms-receiving-images bucket
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'objects'
      AND schemaname = 'storage'
      AND policyname LIKE '%receiving_images%';

    IF policy_count < 4 THEN
        RAISE WARNING 'Expected 4 policies for pms-receiving-images bucket, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: Storage policies for pms-receiving-images bucket created (% policies)', policy_count;
    RAISE NOTICE '  - Path format: {yacht_id}/receiving/{receiving_id}/{filename}';
    RAISE NOTICE '  - SELECT: All crew (yacht-scoped)';
    RAISE NOTICE '  - INSERT/UPDATE: HOD+ (yacht-scoped)';
    RAISE NOTICE '  - DELETE: Manager only';
END $$;
