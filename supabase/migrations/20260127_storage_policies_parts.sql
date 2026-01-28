-- Migration: 20260127_202_storage_policies_parts.sql
-- Purpose: Storage bucket policies for pms-part-photos (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- pms-part-photos bucket stores:
--   - Part images for catalog
--   - Condition photos
--   - Location photos
--
-- Path pattern: {yacht_id}/parts/{part_id}/{filename}
-- All paths MUST start with yacht_id for RLS enforcement
-- ============================================================================

-- Create bucket if not exists (idempotent)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-part-photos',
    'pms-part-photos',
    false,  -- Private bucket
    10485760,  -- 10MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic']
)
ON CONFLICT (id) DO UPDATE SET
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic'];

-- ============================================================================
-- STORAGE POLICIES
-- ============================================================================

-- Policy: SELECT - Crew can view their yacht's part photos
DROP POLICY IF EXISTS "crew_select_part_photos" ON storage.objects;
CREATE POLICY "crew_select_part_photos"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'pms-part-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- Policy: INSERT - Crew can upload part photos to their yacht's folder
DROP POLICY IF EXISTS "crew_insert_part_photos" ON storage.objects;
CREATE POLICY "crew_insert_part_photos"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'pms-part-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'deckhand'::text,
        'bosun'::text,
        'eto'::text,
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: DELETE - HOD+ can delete part photos
DROP POLICY IF EXISTS "hod_delete_part_photos" ON storage.objects;
CREATE POLICY "hod_delete_part_photos"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'pms-part-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: Service role bypass
DROP POLICY IF EXISTS "service_role_part_photos" ON storage.objects;
CREATE POLICY "service_role_part_photos"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'pms-part-photos')
WITH CHECK (bucket_id = 'pms-part-photos');

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT policyname, cmd FROM pg_policies
-- WHERE tablename = 'objects' AND schemaname = 'storage'
-- AND policyname LIKE '%part_photos%';
