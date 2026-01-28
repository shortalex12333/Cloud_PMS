-- Migration: 202601271306_inventory_storage_policies.sql
-- Purpose: Storage RLS policies for part documents and labels
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- BUCKET: documents (Part Attachments)
-- Path pattern: {yacht_id}/parts/{part_id}/{filename}
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "yacht_part_documents_select" ON storage.objects;
DROP POLICY IF EXISTS "yacht_part_documents_insert" ON storage.objects;
DROP POLICY IF EXISTS "yacht_part_documents_delete" ON storage.objects;

-- SELECT: Users can view documents in their yacht's parts folder
CREATE POLICY "yacht_part_documents_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
    );

-- INSERT: Operational crew can upload documents
CREATE POLICY "yacht_part_documents_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- DELETE: HOD only can delete documents
CREATE POLICY "yacht_part_documents_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- ============================================================================
-- BUCKET: pms-label-pdfs (Part Labels)
-- Path pattern: {yacht_id}/parts/{filename}.pdf
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "yacht_labels_select" ON storage.objects;
DROP POLICY IF EXISTS "yacht_labels_insert" ON storage.objects;

-- SELECT: Users can view labels in their yacht folder
CREATE POLICY "yacht_labels_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    );

-- INSERT: Operational crew can create labels
CREATE POLICY "yacht_labels_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT policyname, cmd FROM pg_policies
-- WHERE tablename = 'objects' AND schemaname = 'storage'
-- AND policyname LIKE 'yacht_%';
-- Should return:
-- yacht_part_documents_select, yacht_part_documents_insert, yacht_part_documents_delete
-- yacht_labels_select, yacht_labels_insert
