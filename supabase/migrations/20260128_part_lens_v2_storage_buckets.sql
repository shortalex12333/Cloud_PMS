-- =============================================================================
-- Migration: Part Lens v2 Storage Buckets + RLS
-- =============================================================================
-- Purpose: Create storage buckets for Part Lens v2 with yacht-isolated RLS
-- Buckets: pms-part-photos, pms-receiving-images, pms-label-pdfs
-- Pattern: Same as migration 08 (documents bucket)
-- =============================================================================

-- =============================================================================
-- 1. CREATE STORAGE BUCKETS
-- =============================================================================

-- Bucket 1: Part catalog photos (attached to pms_parts)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-part-photos',
    'pms-part-photos',
    false,  -- Private bucket (requires auth)
    5242880,  -- 5MB limit per photo
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic']
)
ON CONFLICT (id) DO NOTHING;

-- Bucket 2: Receiving/goods receipt images (linked via pms_inventory_transactions.photo_storage_path)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-receiving-images',
    'pms-receiving-images',
    false,
    10485760,  -- 10MB limit (receipt photos may include docs)
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'application/pdf']
)
ON CONFLICT (id) DO NOTHING;

-- Bucket 3: Part label PDFs (generated labels for printing)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-label-pdfs',
    'pms-label-pdfs',
    false,
    2097152,  -- 2MB limit (labels are small PDFs)
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 2. RLS POLICIES - Yacht Isolation
-- =============================================================================
-- Pattern: Users can only access files in folders matching their yacht_id
-- Path format: {bucket}/{yacht_id}/{category}/{filename}
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Bucket 1: pms-part-photos
-- -----------------------------------------------------------------------------

-- Policy: SELECT (read) - Users can view photos for their yacht's parts
DROP POLICY IF EXISTS "Users read yacht part photos" ON storage.objects;
CREATE POLICY "Users read yacht part photos"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

-- Policy: INSERT - Users can upload photos for their yacht's parts
DROP POLICY IF EXISTS "Users upload yacht part photos" ON storage.objects;
CREATE POLICY "Users upload yacht part photos"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

-- Policy: UPDATE - Users can update photos for their yacht (metadata, etc.)
DROP POLICY IF EXISTS "Users update yacht part photos" ON storage.objects;
CREATE POLICY "Users update yacht part photos"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

-- Policy: DELETE - Users can delete photos for their yacht
DROP POLICY IF EXISTS "Users delete yacht part photos" ON storage.objects;
CREATE POLICY "Users delete yacht part photos"
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
);

-- -----------------------------------------------------------------------------
-- Bucket 2: pms-receiving-images
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users read yacht receiving images" ON storage.objects;
CREATE POLICY "Users read yacht receiving images"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'pms-receiving-images'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users upload yacht receiving images" ON storage.objects;
CREATE POLICY "Users upload yacht receiving images"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'pms-receiving-images'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users update yacht receiving images" ON storage.objects;
CREATE POLICY "Users update yacht receiving images"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'pms-receiving-images'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users delete yacht receiving images" ON storage.objects;
CREATE POLICY "Users delete yacht receiving images"
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
);

-- -----------------------------------------------------------------------------
-- Bucket 3: pms-label-pdfs
-- -----------------------------------------------------------------------------
-- NOTE: Labels are generated PDFs, typically manager-only for deletion
-- All authenticated users can read/generate, but delete is yacht-scoped
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users read yacht label pdfs" ON storage.objects;
CREATE POLICY "Users read yacht label pdfs"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'pms-label-pdfs'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users upload yacht label pdfs" ON storage.objects;
CREATE POLICY "Users upload yacht label pdfs"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'pms-label-pdfs'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users update yacht label pdfs" ON storage.objects;
CREATE POLICY "Users update yacht label pdfs"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'pms-label-pdfs'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users delete yacht label pdfs" ON storage.objects;
CREATE POLICY "Users delete yacht label pdfs"
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
);

-- =============================================================================
-- 3. ADD STORAGE PATH COLUMNS TO TABLES
-- =============================================================================
-- Link database tables to storage bucket paths
-- =============================================================================

-- Add photo columns to pms_parts (for catalog photos)
ALTER TABLE public.pms_parts
ADD COLUMN IF NOT EXISTS photo_paths TEXT[] DEFAULT '{}';

COMMENT ON COLUMN public.pms_parts.photo_paths IS
  'Array of storage paths in pms-part-photos bucket. Format: {yacht_id}/parts/{part_id}/{filename}';

-- Note: pms_inventory_transactions.photo_storage_path already exists (see 202601271210_inventory_tables_transaction_ledger.sql)
-- That column links to pms-receiving-images bucket

-- =============================================================================
-- 4. VERIFICATION
-- =============================================================================

-- Verify buckets created
DO $$
DECLARE
  bucket_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO bucket_count
  FROM storage.buckets
  WHERE id IN ('pms-part-photos', 'pms-receiving-images', 'pms-label-pdfs');

  IF bucket_count = 3 THEN
    RAISE NOTICE '✅ All 3 Part Lens v2 storage buckets created';
  ELSE
    RAISE EXCEPTION '❌ Expected 3 buckets, found %', bucket_count;
  END IF;
END $$;

-- Verify RLS policies created (12 policies total: 4 per bucket)
DO $$
DECLARE
  policy_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'storage'
    AND tablename = 'objects'
    AND policyname LIKE '%yacht%'
    AND (
      policyname LIKE '%part photos%'
      OR policyname LIKE '%receiving images%'
      OR policyname LIKE '%label pdfs%'
    );

  IF policy_count >= 12 THEN
    RAISE NOTICE '✅ All Part Lens v2 storage RLS policies created (% policies)', policy_count;
  ELSE
    RAISE WARNING '⚠️  Expected 12+ policies, found %', policy_count;
  END IF;
END $$;

-- =============================================================================
-- NOTES
-- =============================================================================
-- Storage bucket path conventions:
--
-- pms-part-photos:
--   {yacht_id}/parts/{part_id}/{timestamp}_{filename}.jpg
--   Example: 85fe1119-b04c-41ac-80f1-829d23322598/parts/abc123/20260128_engine_oil_filter.jpg
--
-- pms-receiving-images:
--   {yacht_id}/receiving/{transaction_id}/{timestamp}_{filename}.jpg
--   Example: 85fe1119-b04c-41ac-80f1-829d23322598/receiving/def456/20260128_delivery_photo.jpg
--
-- pms-label-pdfs:
--   {yacht_id}/labels/{part_id}/{timestamp}_label.pdf
--   Example: 85fe1119-b04c-41ac-80f1-829d23322598/labels/abc123/20260128_label.pdf
--
-- RLS Enforcement:
-- - First folder MUST match user's yacht_id (enforced by RLS policies)
-- - Cross-yacht access is blocked (403)
-- - Unauthenticated access is blocked (401)
--
-- Migration Safety:
-- - Uses ON CONFLICT DO NOTHING for idempotency
-- - Uses DROP POLICY IF EXISTS before CREATE POLICY
-- - Uses IF NOT EXISTS for column additions
-- =============================================================================
