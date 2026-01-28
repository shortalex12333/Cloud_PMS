-- Migration: 20260127_203_storage_policies_receiving.sql
-- Purpose: Storage bucket policies for pms-receiving-images (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- pms-receiving-images bucket stores:
--   - Photos of received deliveries
--   - Damage documentation
--   - Packing slip images
--
-- Path pattern: {yacht_id}/receiving/{part_id}/{filename}
-- Linked to receive_part action via photo_storage_path
-- ============================================================================

-- Create bucket if not exists (idempotent)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-receiving-images',
    'pms-receiving-images',
    false,  -- Private bucket
    20971520,  -- 20MB limit (larger for packing slips)
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    file_size_limit = 20971520,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'application/pdf'];

-- ============================================================================
-- STORAGE POLICIES
-- ============================================================================

-- Policy: SELECT - Crew can view their yacht's receiving images
DROP POLICY IF EXISTS "crew_select_receiving_images" ON storage.objects;
CREATE POLICY "crew_select_receiving_images"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- Policy: INSERT - Crew can upload receiving images to their yacht's folder
DROP POLICY IF EXISTS "crew_insert_receiving_images" ON storage.objects;
CREATE POLICY "crew_insert_receiving_images"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'pms-receiving-images'
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

-- Policy: DELETE - HOD+ can delete receiving images
DROP POLICY IF EXISTS "hod_delete_receiving_images" ON storage.objects;
CREATE POLICY "hod_delete_receiving_images"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'pms-receiving-images'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: Service role bypass
DROP POLICY IF EXISTS "service_role_receiving_images" ON storage.objects;
CREATE POLICY "service_role_receiving_images"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'pms-receiving-images')
WITH CHECK (bucket_id = 'pms-receiving-images');

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT policyname, cmd FROM pg_policies
-- WHERE tablename = 'objects' AND schemaname = 'storage'
-- AND policyname LIKE '%receiving%';
