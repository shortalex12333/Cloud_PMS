-- Migration: 20260127_208_storage_policies_labels.sql
-- Purpose: Storage bucket policies for pms-label-pdfs (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- pms-label-pdfs bucket stores:
--   - Generated label PDFs from generate_part_labels action
--   - Barcode/QR code label sheets
--
-- Path pattern: {yacht_id}/parts/{part_id}/labels/{filename}
-- or: {yacht_id}/parts/labels/{filename} (batch labels)
--
-- HOD+ only can generate and manage labels
-- ============================================================================

-- Create bucket if not exists (idempotent)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pms-label-pdfs',
    'pms-label-pdfs',
    false,  -- Private bucket
    52428800,  -- 50MB limit (large batch label jobs)
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    file_size_limit = 52428800,
    allowed_mime_types = ARRAY['application/pdf'];

-- ============================================================================
-- STORAGE POLICIES
-- ============================================================================

-- Policy: SELECT - Crew can view their yacht's label PDFs
DROP POLICY IF EXISTS "crew_select_label_pdfs" ON storage.objects;
CREATE POLICY "crew_select_label_pdfs"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'pms-label-pdfs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- Policy: INSERT - HOD+ can upload label PDFs to their yacht's folder
DROP POLICY IF EXISTS "hod_insert_label_pdfs" ON storage.objects;
CREATE POLICY "hod_insert_label_pdfs"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'pms-label-pdfs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: UPDATE - HOD+ can update label PDFs
DROP POLICY IF EXISTS "hod_update_label_pdfs" ON storage.objects;
CREATE POLICY "hod_update_label_pdfs"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
    bucket_id = 'pms-label-pdfs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
)
WITH CHECK (
    bucket_id = 'pms-label-pdfs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- Policy: DELETE - HOD+ can delete label PDFs
DROP POLICY IF EXISTS "hod_delete_label_pdfs" ON storage.objects;
CREATE POLICY "hod_delete_label_pdfs"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'pms-label-pdfs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: Service role bypass
DROP POLICY IF EXISTS "service_role_label_pdfs" ON storage.objects;
CREATE POLICY "service_role_label_pdfs"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'pms-label-pdfs')
WITH CHECK (bucket_id = 'pms-label-pdfs');

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT policyname, cmd FROM pg_policies
-- WHERE tablename = 'objects' AND schemaname = 'storage'
-- AND policyname LIKE '%label%';

-- Test storage path assertion:
-- The path MUST start with {yacht_id}/
-- Valid: "85fe1119-b04c-41ac-80f1-829d23322598/parts/labels/batch_20260127.pdf"
-- Invalid: "parts/labels/batch_20260127.pdf" (missing yacht_id prefix)
