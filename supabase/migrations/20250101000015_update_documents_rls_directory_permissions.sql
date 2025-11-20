-- Migration: Update documents table RLS for directory-based permissions
-- Purpose: Replace simple yacht_id checks with hierarchical directory permissions
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-01-01
-- Depends on: 20250101000013 (hierarchical storage functions)

-- ============================================================================
-- UPDATE DOCUMENTS TABLE RLS FOR DIRECTORY PERMISSIONS
-- ============================================================================

-- This migration updates the documents table SELECT policy to check
-- role_directory_permissions for ROOT-level access control.
--
-- Key changes:
-- 1. SELECT: Use can_access_document() to check directory permissions
-- 2. Service role policies remain unchanged (bypass all checks)
-- 3. INSERT/UPDATE/DELETE policies remain unchanged

-- ============================================================================
-- POLICY: SELECT (Read Access) - UPDATED
-- ============================================================================
-- Users can view documents IF:
-- - Document belongs to their yacht
-- - AND their role has read permission to that ROOT directory

-- Drop existing policy from migration 002
DROP POLICY IF EXISTS "Users can view documents" ON documents;

-- Create updated policy with directory permission checks
CREATE POLICY "Users can view documents"
ON documents
FOR SELECT
TO authenticated
USING (
  -- Check yacht_id AND directory permissions
  can_access_document(yacht_id, system_path)
);

COMMENT ON POLICY "Users can view documents" ON documents IS
  'Users can view documents if: (1) document is from their yacht, '
  '(2) their role has read permission to that ROOT directory. '
  'Uses role_directory_permissions table via can_access_document() function.';

-- ============================================================================
-- POLICY: INSERT - UNCHANGED (keep existing service_role policy)
-- ============================================================================
-- Service role can insert documents for any yacht/directory
-- No changes needed - policy from migration 010 is correct

-- Verify service_role INSERT policy exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'documents'
      AND policyname = 'Service role can insert documents'
  ) THEN
    -- Create if missing
    CREATE POLICY "Service role can insert documents"
    ON documents
    FOR INSERT
    TO service_role
    WITH CHECK (true);

    RAISE NOTICE '✅ Created service_role INSERT policy';
  ELSE
    RAISE NOTICE 'ℹ️  Service role INSERT policy already exists';
  END IF;
END $$;

-- ============================================================================
-- POLICY: UPDATE - UNCHANGED (keep existing service_role policy)
-- ============================================================================
-- Service role can update processing fields for any document
-- No changes needed - policy from migration 010 is correct

-- Verify service_role UPDATE policy exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'documents'
      AND policyname = 'Service role can update document processing'
  ) THEN
    -- Create if missing
    CREATE POLICY "Service role can update document processing"
    ON documents
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

    RAISE NOTICE '✅ Created service_role UPDATE policy';
  ELSE
    RAISE NOTICE 'ℹ️  Service role UPDATE policy already exists';
  END IF;
END $$;

-- ============================================================================
-- POLICY: DELETE - UNCHANGED (keep existing policies)
-- ============================================================================
-- Service role can delete documents
-- Managers can delete documents from their yacht (existing policy from 002)
-- No changes needed

-- Verify service_role DELETE policy exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'documents'
      AND policyname = 'Service role can delete documents'
  ) THEN
    -- Create if missing
    CREATE POLICY "Service role can delete documents"
    ON documents
    FOR DELETE
    TO service_role
    USING (true);

    RAISE NOTICE '✅ Created service_role DELETE policy';
  ELSE
    RAISE NOTICE 'ℹ️  Service role DELETE policy already exists';
  END IF;
END $$;

-- ============================================================================
-- OPTIONAL: Add directory-aware INSERT policy for authenticated users
-- ============================================================================
-- If you want authenticated users (e.g., admins) to insert documents:

/*
DROP POLICY IF EXISTS "Admins can insert documents" ON documents;

CREATE POLICY "Admins can insert documents"
ON documents
FOR INSERT
TO authenticated
WITH CHECK (
  -- Must be admin role
  (auth.jwt()->>'role') = 'admin'
  -- Must be their yacht
  AND yacht_id = (auth.jwt()->>'yacht_id')::uuid
  -- Must have write permission to that directory
  AND can_role_access_directory(
    yacht_id,
    (auth.jwt()->>'role'),
    extract_root_directory(system_path),
    true  -- Require write permission
  )
);

COMMENT ON POLICY "Admins can insert documents" ON documents IS
  'Admins can manually insert document metadata if they have write access to that directory.';
*/

-- ============================================================================
-- OPTIONAL: Add directory-aware UPDATE policy for authenticated users
-- ============================================================================
-- If you want authenticated users (e.g., managers) to update documents:

/*
DROP POLICY IF EXISTS "Managers can update documents" ON documents;

CREATE POLICY "Managers can update documents"
ON documents
FOR UPDATE
TO authenticated
USING (
  -- Must be manager or admin
  (auth.jwt()->>'role') IN ('manager', 'admin')
  -- Must be their yacht
  AND yacht_id = (auth.jwt()->>'yacht_id')::uuid
  -- Must have write permission to that directory
  AND can_role_access_directory(
    yacht_id,
    (auth.jwt()->>'role'),
    extract_root_directory(system_path),
    true  -- Require write permission
  )
)
WITH CHECK (
  -- Same conditions for updated values
  yacht_id = (auth.jwt()->>'yacht_id')::uuid
  AND can_role_access_directory(
    yacht_id,
    (auth.jwt()->>'role'),
    extract_root_directory(system_path),
    true
  )
);

COMMENT ON POLICY "Managers can update documents" ON documents IS
  'Managers can update document metadata if they have write access to that directory.';
*/

-- ============================================================================
-- UPDATE HELPER FUNCTION: can_access_document_by_path
-- ============================================================================
-- Update existing function to use directory permissions

DROP FUNCTION IF EXISTS public.can_access_document_by_path(text);

CREATE OR REPLACE FUNCTION public.can_access_document_by_path(doc_storage_path text)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
  doc_yacht_id uuid;
  doc_system_path text;
BEGIN
  -- Look up document yacht_id and system_path
  SELECT yacht_id, system_path
  INTO doc_yacht_id, doc_system_path
  FROM documents
  WHERE file_path = doc_storage_path
  LIMIT 1;

  -- If document not found, deny access
  IF doc_yacht_id IS NULL THEN
    RETURN false;
  END IF;

  -- Use directory permission check
  RETURN can_access_document(doc_yacht_id, doc_system_path);
END;
$$;

COMMENT ON FUNCTION public.can_access_document_by_path(text) IS
  'Check if authenticated user can access document by storage path. '
  'Includes yacht isolation AND directory permission checks.';

GRANT EXECUTE ON FUNCTION public.can_access_document_by_path(text) TO authenticated;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  policy_count int;
  select_policy_count int;
BEGIN
  -- Count total policies on documents table
  SELECT COUNT(*)
  INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename = 'documents';

  -- Count SELECT policies specifically
  SELECT COUNT(*)
  INTO select_policy_count
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename = 'documents'
    AND cmd = 'SELECT';

  RAISE NOTICE '✅ Documents table RLS updated for directory permissions';
  RAISE NOTICE 'Total policies on documents table: %', policy_count;
  RAISE NOTICE 'SELECT policies: %', select_policy_count;

  IF select_policy_count = 0 THEN
    RAISE WARNING '⚠️  No SELECT policy found on documents table!';
  END IF;
END $$;

-- List current policies
DO $$
BEGIN
  RAISE NOTICE 'Current documents table policies:';
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
    WHERE schemaname = 'public'
      AND tablename = 'documents'
    ORDER BY cmd, policyname
  );
END $$;

-- ============================================================================
-- TEST QUERIES (for manual verification)
-- ============================================================================

-- Test 1: Check RLS is enabled on documents
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public' AND tablename = 'documents';
-- Expected: rowsecurity = true

-- Test 2: List all policies
-- SELECT
--   policyname,
--   cmd,
--   roles,
--   qual::text as using_clause,
--   with_check::text as with_check_clause
-- FROM pg_policies
-- WHERE schemaname = 'public' AND tablename = 'documents'
-- ORDER BY cmd, policyname;

-- Test 3: Simulate user access
-- SET request.jwt.claims TO '{"yacht_id": "123e4567-e89b-12d3-a456-426614174000", "role": "engineer"}';
-- SELECT filename, system_path
-- FROM documents
-- WHERE yacht_id = '123e4567-e89b-12d3-a456-426614174000'::uuid;
-- Expected: Only documents from directories engineer has access to

-- Test 4: Check accessible directories for current user
-- SELECT * FROM get_accessible_directories();
-- Expected: List of directories based on user's role

-- Test 5: Test can_access_document function
-- SELECT can_access_document(
--   '123e4567-e89b-12d3-a456-426614174000'::uuid,
--   '03_Engineering/MainEngine'
-- );
-- Expected: true (if current role has Engineering access)
