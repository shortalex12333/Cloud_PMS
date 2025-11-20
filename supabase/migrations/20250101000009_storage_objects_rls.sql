-- ============================================================================
-- Migration: Storage Objects RLS Policies
-- Version: 20250101000009
-- Description: Row-Level Security for storage.objects table (bucket access control)
-- ============================================================================
--
-- CRITICAL: These policies enforce yacht-based isolation for Supabase Storage
--
-- Requirements:
-- 1. SELECT (read): Authenticated users can ONLY read files from their yacht's path
-- 2. INSERT (upload): Service role OR authenticated users uploading to their yacht's path
-- 3. UPDATE: Service role only (metadata updates)
-- 4. DELETE: Service role only (no user deletion)
--
-- Path Format:
-- - documents/{yacht_id}/{sha256}/{filename}
-- - raw-uploads/{upload_id}/chunk_X
--
-- DEPENDS ON: Migration 20250101000008 (helper functions MUST exist)
-- ============================================================================

-- ============================================================================
-- ENABLE RLS ON storage.objects
-- ============================================================================

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- POLICY 1: SELECT (Read Access)
-- Users can ONLY read documents from their yacht
-- ============================================================================

DROP POLICY IF EXISTS "Users can read own yacht documents" ON storage.objects;

CREATE POLICY "Users can read own yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  -- Allow if bucket is 'documents' AND yacht_id in path matches user's yacht_id
  (
    bucket_id = 'documents'
    AND extract_yacht_id_from_path(name) = get_yacht_id()
  )
  OR
  -- Allow if bucket is 'raw-uploads' AND user is uploading (future: more restrictive)
  (
    bucket_id = 'raw-uploads'
    AND extract_yacht_id_from_path(name) = get_yacht_id()
  )
);

COMMENT ON POLICY "Users can read own yacht documents" ON storage.objects IS
  'Authenticated users can only read documents from their yacht path';

-- ============================================================================
-- POLICY 2: INSERT (Upload Access)
-- Service role can upload anywhere
-- Authenticated users can ONLY upload to their yacht's path
-- ============================================================================

DROP POLICY IF EXISTS "Service role can upload documents" ON storage.objects;

CREATE POLICY "Service role can upload documents"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (true);  -- Service role can upload anywhere

COMMENT ON POLICY "Service role can upload documents" ON storage.objects IS
  'Service role (n8n, ingestion) can upload to any path';

-- Policy for authenticated users uploading to their own yacht
DROP POLICY IF EXISTS "Users can upload to own yacht path" ON storage.objects;

CREATE POLICY "Users can upload to own yacht path"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  -- Bucket must be documents or raw-uploads
  bucket_id IN ('documents', 'raw-uploads')
  -- Path must start with user's yacht_id
  AND extract_yacht_id_from_path(name) = get_yacht_id()
  -- Path format must be valid
  AND validate_storage_path_format(name, bucket_id)
);

COMMENT ON POLICY "Users can upload to own yacht path" ON storage.objects IS
  'Authenticated users can upload documents to their yacht path only';

-- ============================================================================
-- POLICY 3: UPDATE (Metadata Updates)
-- Service role only
-- ============================================================================

DROP POLICY IF EXISTS "Service role can update storage objects" ON storage.objects;

CREATE POLICY "Service role can update storage objects"
ON storage.objects
FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

COMMENT ON POLICY "Service role can update storage objects" ON storage.objects IS
  'Only service role can update storage object metadata';

-- ============================================================================
-- POLICY 4: DELETE (File Deletion)
-- Service role only
-- ============================================================================

DROP POLICY IF EXISTS "Service role can delete documents" ON storage.objects;

CREATE POLICY "Service role can delete documents"
ON storage.objects
FOR DELETE
TO service_role
USING (true);

COMMENT ON POLICY "Service role can delete documents" ON storage.objects IS
  'Only service role can delete documents (users cannot delete)';

-- ============================================================================
-- ADDITIONAL: Anon access (for signed URLs)
-- ============================================================================

-- Signed URLs work because they include temporary auth token
-- No separate anon policy needed - signed URLs bypass RLS when valid

-- ============================================================================
-- VERIFICATION QUERIES (run separately to test)
-- ============================================================================

-- Check RLS is enabled:
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'storage' AND tablename = 'objects';
-- Expected: rowsecurity = true

-- List all policies on storage.objects:
-- SELECT policyname, permissive, roles, cmd
-- FROM pg_policies
-- WHERE schemaname = 'storage' AND tablename = 'objects'
-- ORDER BY policyname;

-- Expected policies:
-- 1. "Users can read own yacht documents" (SELECT, authenticated)
-- 2. "Service role can upload documents" (INSERT, service_role)
-- 3. "Users can upload to own yacht path" (INSERT, authenticated)
-- 4. "Service role can update storage objects" (UPDATE, service_role)
-- 5. "Service role can delete documents" (DELETE, service_role)
