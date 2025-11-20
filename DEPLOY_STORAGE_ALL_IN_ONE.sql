-- ============================================================================
-- Migration: Create Storage Buckets for Document Management
-- Version: 20250101000007
-- Description: Create Supabase Storage buckets for multi-yacht document isolation
-- ============================================================================
--
-- CRITICAL: This migration creates storage buckets for:
-- 1. documents - Final validated documents (production)
-- 2. raw-uploads - Temporary pre-assembled uploads (optional, for chunked uploads)
--
-- Path Convention:
-- - documents/{yacht_id}/{sha256}/{original_filename}
-- - raw-uploads/{upload_id}/chunk_X
-- ============================================================================

-- ============================================================================
-- BUCKET 1: documents (Production Documents)
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'documents',
  'documents',
  false,  -- NOT public (RLS enforced)
  524288000,  -- 500 MB max file size
  ARRAY[
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/msword',
    'application/vnd.ms-excel',
    'text/plain',
    'text/csv',
    'application/zip',
    'application/x-zip-compressed'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

COMMENT ON TABLE storage.buckets IS 'Supabase Storage buckets configuration';

-- ============================================================================
-- BUCKET 2: raw-uploads (Temporary Uploads - Optional)
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'raw-uploads',
  'raw-uploads',
  false,  -- NOT public (RLS enforced)
  1073741824,  -- 1 GB max (for chunked uploads)
  NULL  -- Allow all MIME types (temporary storage)
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to verify)
-- ============================================================================

-- Verify buckets created:
-- SELECT id, name, public, file_size_limit, created_at
-- FROM storage.buckets
-- WHERE id IN ('documents', 'raw-uploads');

-- Expected: 2 buckets
-- documents: public=false, file_size_limit=524288000
-- raw-uploads: public=false, file_size_limit=1073741824
-- ============================================================================
-- Migration: Storage Helper Functions
-- Version: 20250101000008
-- Description: Helper functions for yacht-based storage path validation
-- ============================================================================
--
-- CRITICAL: These functions MUST be created BEFORE storage RLS policies
-- They are referenced in RLS policy USING/WITH CHECK clauses
-- ============================================================================

-- ============================================================================
-- FUNCTION: get_yacht_id()
-- Purpose: Extract yacht_id from JWT claims
-- Used by: Storage RLS policies, metadata RLS policies
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_yacht_id()
RETURNS text
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Extract yacht_id from JWT claims
  -- Supabase JWT structure: auth.jwt() returns jsonb
  -- Claims are in the top level: {"yacht_id": "...", "sub": "...", ...}
  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'yacht_id', '')::text;
$$;

COMMENT ON FUNCTION public.get_yacht_id IS 'Extract yacht_id from JWT claims for RLS enforcement';

-- Alternative implementation using auth.jwt() if available
-- Note: current_setting is more reliable across Supabase versions
CREATE OR REPLACE FUNCTION public.get_yacht_id_from_user()
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Fallback: lookup yacht_id from users table using auth.uid()
  SELECT yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_yacht_id_from_user IS 'Get yacht_id by looking up auth user in users table';

-- ============================================================================
-- FUNCTION: extract_yacht_id_from_path(storage_path)
-- Purpose: Extract yacht_id from storage path
-- Path format: documents/{yacht_id}/{sha256}/{filename}
-- ============================================================================

CREATE OR REPLACE FUNCTION public.extract_yacht_id_from_path(storage_path text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  -- Extract yacht_id from path
  -- Path format: documents/{yacht_id}/...
  -- OR: raw-uploads/{yacht_id}/...
  -- Split by '/' and get second segment (index 2)
  SELECT split_part(storage_path, '/', 2);
$$;

COMMENT ON FUNCTION public.extract_yacht_id_from_path IS 'Extract yacht_id from storage path (2nd segment)';

-- ============================================================================
-- FUNCTION: assert_valid_yacht_path(storage_path)
-- Purpose: Validate that storage path matches user's yacht_id
-- Throws exception if invalid
-- ============================================================================

CREATE OR REPLACE FUNCTION public.assert_valid_yacht_path(storage_path text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id text;
  path_yacht_id text;
BEGIN
  -- Get user's yacht_id from JWT
  user_yacht_id := get_yacht_id();

  IF user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'No yacht_id found in JWT claims';
  END IF;

  -- Extract yacht_id from storage path
  path_yacht_id := extract_yacht_id_from_path(storage_path);

  IF path_yacht_id IS NULL OR path_yacht_id = '' THEN
    RAISE EXCEPTION 'Invalid storage path format: %. Expected format: bucket/{yacht_id}/...', storage_path;
  END IF;

  -- Validate match
  IF user_yacht_id != path_yacht_id THEN
    RAISE EXCEPTION 'Yacht ID mismatch. JWT yacht_id: %, Path yacht_id: %', user_yacht_id, path_yacht_id;
  END IF;

  RETURN true;
END;
$$;

COMMENT ON FUNCTION public.assert_valid_yacht_path IS 'Validate storage path matches user yacht_id, throws exception if invalid';

-- ============================================================================
-- FUNCTION: can_access_document(storage_path)
-- Purpose: Boolean check if user can access document at given path
-- Returns true/false (no exception)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.can_access_document(storage_path text)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT get_yacht_id() = extract_yacht_id_from_path(storage_path);
$$;

COMMENT ON FUNCTION public.can_access_document IS 'Check if user can access document at given storage path';

-- ============================================================================
-- FUNCTION: is_service_role()
-- Purpose: Check if current request is using service_role key
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_service_role()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Check if role is service_role (bypasses RLS)
  SELECT auth.role() = 'service_role';
$$;

COMMENT ON FUNCTION public.is_service_role IS 'Check if current request is using service_role key';

-- ============================================================================
-- FUNCTION: validate_storage_path_format(storage_path, bucket_name)
-- Purpose: Validate storage path follows the correct format
-- ============================================================================

CREATE OR REPLACE FUNCTION public.validate_storage_path_format(
  storage_path text,
  bucket_name text
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  path_segments text[];
BEGIN
  -- Split path by '/'
  path_segments := string_to_array(storage_path, '/');

  -- Validate based on bucket
  IF bucket_name = 'documents' THEN
    -- Expected format: {yacht_id}/{sha256}/{filename}
    -- Minimum 3 segments
    IF array_length(path_segments, 1) < 3 THEN
      RETURN false;
    END IF;

    -- Validate yacht_id format (UUID)
    IF NOT (path_segments[1] ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') THEN
      RETURN false;
    END IF;

    -- Validate sha256 format (64 hex chars)
    IF NOT (path_segments[2] ~ '^[a-f0-9]{64}$') THEN
      RETURN false;
    END IF;

  ELSIF bucket_name = 'raw-uploads' THEN
    -- Expected format: {upload_id}/chunk_X
    -- Minimum 2 segments
    IF array_length(path_segments, 1) < 2 THEN
      RETURN false;
    END IF;

  END IF;

  RETURN true;
END;
$$;

COMMENT ON FUNCTION public.validate_storage_path_format IS 'Validate storage path follows correct format for bucket';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION public.get_yacht_id() TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_yacht_id_from_user() TO authenticated;
GRANT EXECUTE ON FUNCTION public.extract_yacht_id_from_path(text) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.assert_valid_yacht_path(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.can_access_document(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_service_role() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.validate_storage_path_format(text, text) TO authenticated, service_role;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to test)
-- ============================================================================

-- Test get_yacht_id() (requires authenticated user with yacht_id in JWT):
-- SELECT get_yacht_id();

-- Test extract_yacht_id_from_path():
-- SELECT extract_yacht_id_from_path('550e8400-e29b-41d4-a716-446655440000/abc123.../test.pdf');
-- Expected: '550e8400-e29b-41d4-a716-446655440000'

-- Test validate_storage_path_format():
-- SELECT validate_storage_path_format('550e8400-e29b-41d4-a716-446655440000/a1b2c3d4.../file.pdf', 'documents');
-- Expected: true/false based on format
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
-- ============================================================================
-- Migration: Documents Metadata Table RLS Policies
-- Version: 20250101000010
-- Description: Row-Level Security for documents table (metadata records)
-- ============================================================================
--
-- CRITICAL: These policies enforce yacht-based isolation for document metadata
--
-- Requirements:
-- 1. SELECT: Users can ONLY see documents from their yacht
-- 2. INSERT: Service role (ingestion) can insert new documents
-- 3. UPDATE: Service role (indexing) can update processing fields
-- 4. DELETE: Service role only (no user deletion)
--
-- The documents table was created in migration 20250101000001 (initial_schema_v2.sql)
-- This migration ONLY adds RLS policies specific to storage operations
-- ============================================================================

-- NOTE: RLS is already enabled on documents table from migration 002
-- This migration adds ADDITIONAL policies specific to storage/ingestion workflow

-- ============================================================================
-- POLICY: SELECT (Read Access)
-- Already exists from migration 002: "Users can view documents"
-- Verifying it matches storage requirements
-- ============================================================================

-- This policy already exists from RLS migration 002:
-- CREATE POLICY "Users can view documents"
--   ON documents FOR SELECT
--   USING (yacht_id = get_user_yacht_id());

-- No changes needed - this policy correctly enforces yacht isolation

-- ============================================================================
-- POLICY: INSERT (Ingestion Service)
-- Already exists from migration 002: "System can insert documents"
-- Verifying it allows service_role
-- ============================================================================

-- This policy already exists from RLS migration 002:
-- CREATE POLICY "System can insert documents"
--   ON documents FOR INSERT
--   WITH CHECK (yacht_id = get_user_yacht_id());

-- This policy is TOO RESTRICTIVE for service_role ingestion
-- Service role needs to insert documents for ANY yacht
-- Let's add a specific policy for service_role

DROP POLICY IF EXISTS "Service role can insert documents" ON documents;

CREATE POLICY "Service role can insert documents"
ON documents
FOR INSERT
TO service_role
WITH CHECK (true);  -- Service role can insert for any yacht

COMMENT ON POLICY "Service role can insert documents" ON documents IS
  'Service role (n8n ingestion) can insert document metadata for any yacht';

-- ============================================================================
-- POLICY: UPDATE (Indexing Service)
-- Service role can update indexed status and embedding job fields
-- ============================================================================

-- Existing policy from migration 002 allows managers to manage documents
-- We need to ensure service_role can update processing fields

DROP POLICY IF EXISTS "Service role can update document processing" ON documents;

CREATE POLICY "Service role can update document processing"
ON documents
FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

COMMENT ON POLICY "Service role can update document processing" ON documents IS
  'Service role (indexing pipeline) can update processing fields (indexed, indexed_at)';

-- ============================================================================
-- POLICY: DELETE (Service Role Only)
-- Existing "Managers can manage documents" policy from migration 002
-- Adding explicit service_role delete policy
-- ============================================================================

-- Managers can delete (existing policy from migration 002)
-- Adding service_role explicit permission

DROP POLICY IF EXISTS "Service role can delete documents" ON documents;

CREATE POLICY "Service role can delete documents"
ON documents
FOR DELETE
TO service_role
USING (true);

COMMENT ON POLICY "Service role can delete documents" ON documents IS
  'Service role can delete document metadata records';

-- ============================================================================
-- ADDITIONAL HELPER: Document access by storage_path
-- Function to check if user can access document by storage_path
-- ============================================================================

CREATE OR REPLACE FUNCTION public.can_access_document_by_path(doc_storage_path text)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Check if user's yacht_id matches the yacht_id in documents table
  SELECT EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.storage_path = doc_storage_path
      AND d.yacht_id = get_user_yacht_id()
  );
$$;

COMMENT ON FUNCTION public.can_access_document_by_path IS
  'Check if authenticated user can access document by storage_path';

GRANT EXECUTE ON FUNCTION public.can_access_document_by_path(text) TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to test)
-- ============================================================================

-- List all policies on documents table:
-- SELECT policyname, permissive, roles, cmd
-- FROM pg_policies
-- WHERE schemaname = 'public' AND tablename = 'documents'
-- ORDER BY policyname;

-- Expected policies (from migration 002 + this migration):
-- 1. "Users can view documents" (SELECT, authenticated) - from migration 002
-- 2. "System can insert documents" (INSERT, authenticated) - from migration 002
-- 3. "Managers can manage documents" (ALL, authenticated) - from migration 002
-- 4. "Service role can insert documents" (INSERT, service_role) - NEW
-- 5. "Service role can update document processing" (UPDATE, service_role) - NEW
-- 6. "Service role can delete documents" (DELETE, service_role) - NEW

-- Test document access:
-- SELECT * FROM documents WHERE yacht_id = get_user_yacht_id();
-- Should only return documents from user's yacht
