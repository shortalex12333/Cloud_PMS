-- =============================================================================
-- Migration: Part Lens v2 Storage - Manager-Only DELETE
-- =============================================================================
-- Purpose: Replace yacht-scoped DELETE policies with manager-only DELETE
-- Per doctrine: Only managers can delete storage objects
-- Affected buckets: pms-part-photos, pms-receiving-images, pms-label-pdfs
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Bucket 1: pms-part-photos - Manager-only DELETE
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users delete yacht part photos" ON storage.objects;
CREATE POLICY "Managers delete yacht part photos"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
  AND public.is_manager(auth.uid())  -- Manager-only
);

-- -----------------------------------------------------------------------------
-- Bucket 2: pms-receiving-images - Manager-only DELETE
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users delete yacht receiving images" ON storage.objects;
CREATE POLICY "Managers delete yacht receiving images"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'pms-receiving-images'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
  AND public.is_manager(auth.uid())  -- Manager-only
);

-- -----------------------------------------------------------------------------
-- Bucket 3: pms-label-pdfs - Manager-only DELETE
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users delete yacht label pdfs" ON storage.objects;
CREATE POLICY "Managers delete yacht label pdfs"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'pms-label-pdfs'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
  AND public.is_manager(auth.uid())  -- Manager-only
);

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
  policy_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'storage'
    AND tablename = 'objects'
    AND cmd = 'DELETE'
    AND policyname LIKE 'Managers delete%'
    AND (
      policyname LIKE '%part photos%'
      OR policyname LIKE '%receiving images%'
      OR policyname LIKE '%label pdfs%'
    );

  IF policy_count = 3 THEN
    RAISE NOTICE '✅ All 3 manager-only DELETE policies created';
  ELSE
    RAISE EXCEPTION '❌ Expected 3 DELETE policies, found %', policy_count;
  END IF;
END $$;

-- =============================================================================
-- NOTES
-- =============================================================================
-- Manager-only DELETE enforcement:
-- - Crew: Can read/upload, CANNOT delete (403)
-- - HOD: Can read/upload, CANNOT delete (403)
-- - Manager: Can read/upload/delete (204 on success)
--
-- Cross-yacht protection:
-- - DELETE requires yacht_id match + manager role
-- - Cross-yacht delete attempts → 403
-- =============================================================================
