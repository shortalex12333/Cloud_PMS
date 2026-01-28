-- ============================================================================
-- MIGRATION: 20260127_011_documents_storage_write_policies.sql
-- PURPOSE: Storage bucket policies for equipment documents
-- LENS: Equipment Lens v2
-- PATH: {yacht_id}/equipment/{equipment_id}/{filename}
-- ============================================================================

-- Note: Equipment files go to 'documents' bucket
-- Path pattern: {yacht_id}/equipment/{equipment_id}/{filename}
-- storage.foldername(name)[1] extracts yacht_id from path

-- DROP existing equipment-specific policies for idempotency
DROP POLICY IF EXISTS "Crew read equipment documents" ON storage.objects;
DROP POLICY IF EXISTS "Crew upload equipment documents" ON storage.objects;
DROP POLICY IF EXISTS "HOD update equipment documents" ON storage.objects;
DROP POLICY IF EXISTS "Manager delete equipment documents" ON storage.objects;

-- SELECT: Yacht users can read their yacht's equipment documents
CREATE POLICY "Crew read equipment documents"
ON storage.objects
FOR SELECT TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND (storage.foldername(name))[2] = 'equipment'
);

-- INSERT: All crew can upload to their yacht's equipment folder
CREATE POLICY "Crew upload equipment documents"
ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND (storage.foldername(name))[2] = 'equipment'
);

-- UPDATE: HOD can update metadata
CREATE POLICY "HOD update equipment documents"
ON storage.objects
FOR UPDATE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND (storage.foldername(name))[2] = 'equipment'
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- DELETE: Manager only
CREATE POLICY "Manager delete equipment documents"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND (storage.foldername(name))[2] = 'equipment'
    AND public.is_manager()
);

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment storage policies created for documents bucket';
END $$;
