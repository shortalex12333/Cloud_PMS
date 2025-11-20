-- Migration: Update storage.objects RLS for directory-based permissions
-- Purpose: Replace simple yacht_id checks with hierarchical directory permissions
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-01-01
-- Depends on: 20250101000013 (hierarchical storage functions)

-- ============================================================================
-- UPDATE STORAGE.OBJECTS RLS POLICIES FOR DIRECTORY PERMISSIONS
-- ============================================================================

-- This migration replaces the existing storage RLS policies with enhanced
-- versions that check role_directory_permissions for ROOT-level access control.
--
-- Key changes:
-- 1. SELECT: Use can_access_storage_path() to check directory permissions
-- 2. INSERT: Use can_upload_to_storage_path() to check write permissions
-- 3. Service role policies remain unchanged (bypass all checks)

-- ============================================================================
-- POLICY 1: SELECT (Read Access) - UPDATED
-- ============================================================================
-- Users can read documents IF:
-- - File is in their yacht's path
-- - AND their role has read permission to that ROOT directory

DROP POLICY IF EXISTS "Users can read own yacht documents" ON storage.objects;

CREATE POLICY "Users can read own yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  -- Documents bucket: check yacht + directory permissions
  (
    bucket_id = 'documents'
    AND can_access_storage_path(name)
  )
  OR
  -- Raw-uploads bucket: yacht isolation only (temporary uploads)
  (
    bucket_id = 'raw-uploads'
    AND extract_yacht_id_from_storage_path(name) = (auth.jwt()->>'yacht_id')::uuid
  )
);

COMMENT ON POLICY "Users can read own yacht documents" ON storage.objects IS
  'Users can read documents if: (1) file is in their yacht path, '
  '(2) their role has read permission to that ROOT directory. '
  'Uses role_directory_permissions table.';

-- ============================================================================
-- POLICY 2: INSERT (Upload Access) - UPDATED
-- ============================================================================
-- Authenticated users can upload IF:
-- - Uploading to their yacht's path
-- - AND their role has write permission to that ROOT directory

-- Service role policy: unchanged (can upload anywhere)
DROP POLICY IF EXISTS "Service role can upload documents" ON storage.objects;

CREATE POLICY "Service role can upload documents"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (true);  -- Service role bypasses all checks

COMMENT ON POLICY "Service role can upload documents" ON storage.objects IS
  'Service role (Worker 4/5, n8n) can upload to any path. '
  'Bypasses directory permission checks.';

-- Authenticated user policy: check write permissions
DROP POLICY IF EXISTS "Users can upload to own yacht path" ON storage.objects;

CREATE POLICY "Users can upload to own yacht path"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  -- Documents bucket: check yacht + write permissions
  (
    bucket_id = 'documents'
    AND can_upload_to_storage_path(name)
  )
  OR
  -- Raw-uploads bucket: yacht isolation only (less restrictive)
  (
    bucket_id = 'raw-uploads'
    AND extract_yacht_id_from_storage_path(name) = (auth.jwt()->>'yacht_id')::uuid
    AND validate_storage_path_format(name, 'raw-uploads')
  )
);

COMMENT ON POLICY "Users can upload to own yacht path" ON storage.objects IS
  'Users can upload if: (1) uploading to their yacht path, '
  '(2) their role has WRITE permission to that ROOT directory. '
  'More restrictive than read access.';

-- ============================================================================
-- POLICY 3: UPDATE (Metadata Updates) - UNCHANGED
-- ============================================================================
-- Service role only - no changes needed

DROP POLICY IF EXISTS "Service role can update storage objects" ON storage.objects;

CREATE POLICY "Service role can update storage objects"
ON storage.objects
FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

COMMENT ON POLICY "Service role can update storage objects" ON storage.objects IS
  'Only service role can update storage object metadata. '
  'Users cannot modify file metadata.';

-- ============================================================================
-- POLICY 4: DELETE (File Deletion) - UNCHANGED
-- ============================================================================
-- Service role only - no changes needed

DROP POLICY IF EXISTS "Service role can delete documents" ON storage.objects;

CREATE POLICY "Service role can delete documents"
ON storage.objects
FOR DELETE
TO service_role
USING (true);

COMMENT ON POLICY "Service role can delete documents" ON storage.objects IS
  'Only service role can delete files. '
  'Users cannot delete documents (audit trail preservation).';

-- ============================================================================
-- OPTIONAL: Add admin DELETE policy (if admins should be able to delete)
-- ============================================================================
-- Uncomment if yacht admins should have delete permissions

/*
DROP POLICY IF EXISTS "Admins can delete own yacht documents" ON storage.objects;

CREATE POLICY "Admins can delete own yacht documents"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  -- Must be admin role
  (auth.jwt()->>'role') = 'admin'
  -- Must be in their yacht's path
  AND extract_yacht_id_from_storage_path(name) = (auth.jwt()->>'yacht_id')::uuid
  -- Must be documents bucket
  AND bucket_id = 'documents'
);

COMMENT ON POLICY "Admins can delete own yacht documents" ON storage.objects IS
  'Yacht admins can delete documents from their yacht. '
  'Requires admin role in JWT claims.';
*/

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  policy_count int;
BEGIN
  -- Count policies on storage.objects
  SELECT COUNT(*)
  INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'storage'
    AND tablename = 'objects';

  RAISE NOTICE '✅ Storage RLS policies updated for directory permissions';
  RAISE NOTICE 'Total policies on storage.objects: %', policy_count;

  IF policy_count < 5 THEN
    RAISE WARNING '⚠️  Expected at least 5 policies, found %', policy_count;
  END IF;
END $$;

-- List all policies
DO $$
BEGIN
  RAISE NOTICE 'Current storage.objects policies:';
  RAISE NOTICE '%', (
    SELECT string_agg(
      format('  [%s] %s → %s',
        cmd,
        policyname,
        roles::text
      ),
      E'\n'
    )
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
    ORDER BY cmd, policyname
  );
END $$;

-- ============================================================================
-- TEST QUERIES (for manual verification)
-- ============================================================================

-- Test 1: Check if RLS is enabled
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'storage' AND tablename = 'objects';
-- Expected: rowsecurity = true

-- Test 2: View all policies
-- SELECT
--   policyname,
--   permissive,
--   roles,
--   cmd,
--   qual,  -- USING clause
--   with_check  -- WITH CHECK clause
-- FROM pg_policies
-- WHERE schemaname = 'storage' AND tablename = 'objects'
-- ORDER BY cmd, policyname;

-- Test 3: Simulate access check for a user
-- SET request.jwt.claims TO '{"yacht_id": "123e4567-e89b-12d3-a456-426614174000", "role": "engineer"}';
-- SELECT can_access_storage_path('documents/123e4567-e89b-12d3-a456-426614174000/Engineering/MainEngine/manual.pdf');
-- Expected: true (if engineer has Engineering directory access)

-- Test 4: Simulate access check for wrong directory
-- SET request.jwt.claims TO '{"yacht_id": "123e4567-e89b-12d3-a456-426614174000", "role": "engineer"}';
-- SELECT can_access_storage_path('documents/123e4567-e89b-12d3-a456-426614174000/Bridge/Charts/nav.pdf');
-- Expected: false (engineer should not have Bridge access)

-- Test 5: List accessible directories for current user
-- SELECT * FROM get_accessible_directories();
-- Expected: List of directories based on user's role
