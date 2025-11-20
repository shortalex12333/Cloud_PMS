-- Migration: Hierarchical storage helper functions
-- Purpose: Path validation and permission checking for directory-based RLS
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-01-01

-- ============================================================================
-- CORE HELPER FUNCTIONS FOR HIERARCHICAL STORAGE
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Extract yacht_id from storage path
-- ----------------------------------------------------------------------------
-- Path format: documents/{yacht_id}/{system_path}/{filename}
-- Example: documents/7b2c.../03_Engineering/MainEngine/manual.pdf

CREATE OR REPLACE FUNCTION public.extract_yacht_id_from_storage_path(storage_path text)
RETURNS uuid
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT NULLIF(split_part(storage_path, '/', 2), '')::uuid;
$$;

COMMENT ON FUNCTION public.extract_yacht_id_from_storage_path(text) IS
  'Extracts yacht_id from storage path. '
  'Example: "documents/123.../Engineering/file.pdf" → 123...';

-- ----------------------------------------------------------------------------
-- Extract system_path from storage path
-- ----------------------------------------------------------------------------
-- Returns the hierarchical path portion (between yacht_id and filename)

CREATE OR REPLACE FUNCTION public.extract_system_path_from_storage(storage_path text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT regexp_replace(
    storage_path,
    '^documents/[^/]+/(.+)/[^/]+$',  -- Match: documents/yacht/{system_path}/filename
    '\1'
  );
$$;

COMMENT ON FUNCTION public.extract_system_path_from_storage(text) IS
  'Extracts system_path from storage path. '
  'Example: "documents/123/Engineering/Main/file.pdf" → "Engineering/Main"';

-- ----------------------------------------------------------------------------
-- Extract ROOT directory from storage path
-- ----------------------------------------------------------------------------
-- Returns the first component of system_path

CREATE OR REPLACE FUNCTION public.extract_root_directory_from_storage(storage_path text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT split_part(
    extract_system_path_from_storage(storage_path),
    '/',
    1
  );
$$;

COMMENT ON FUNCTION public.extract_root_directory_from_storage(text) IS
  'Extracts ROOT directory from storage path. '
  'Example: "documents/123/Engineering/Main/file.pdf" → "Engineering"';

-- ----------------------------------------------------------------------------
-- Validate storage path format
-- ----------------------------------------------------------------------------
-- Ensures path follows canonical format

CREATE OR REPLACE FUNCTION public.validate_storage_path_format(
  storage_path text,
  bucket_id text DEFAULT 'documents'
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  expected_pattern text;
BEGIN
  -- Pattern: documents/{uuid}/{system_path}/{filename}
  -- - At least 4 path segments
  -- - Second segment is valid UUID
  -- - No leading/trailing slashes
  -- - No double slashes

  expected_pattern := '^' || bucket_id || '/[0-9a-f\-]{36}/.+/[^/]+$';

  RETURN (
    storage_path ~ expected_pattern
    AND storage_path !~ '//'
    AND storage_path !~ '^/'
    AND storage_path !~ '/$'
  );
END;
$$;

COMMENT ON FUNCTION public.validate_storage_path_format(text, text) IS
  'Validates storage path follows canonical format: bucket/{uuid}/{system_path}/{filename}. '
  'Returns false if path is malformed.';

-- ----------------------------------------------------------------------------
-- Assert valid yacht path (throws error if invalid)
-- ----------------------------------------------------------------------------
-- Used in constraints and checks where we want to fail fast

CREATE OR REPLACE FUNCTION public.assert_valid_yacht_path(
  storage_path text,
  bucket_id text DEFAULT 'documents'
)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  IF NOT validate_storage_path_format(storage_path, bucket_id) THEN
    RAISE EXCEPTION 'Invalid storage path format: %. Expected: %/{uuid}/{system_path}/{filename}',
      storage_path, bucket_id;
  END IF;

  RETURN true;
END;
$$;

COMMENT ON FUNCTION public.assert_valid_yacht_path(text, text) IS
  'Validates storage path and throws exception if invalid. '
  'Use in CHECK constraints or validation logic.';

-- ============================================================================
-- PERMISSION CHECKING FUNCTIONS (CORE RLS LOGIC)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Check if current user can access a storage path
-- ----------------------------------------------------------------------------
-- This is the MAIN RLS function used by storage.objects policies

CREATE OR REPLACE FUNCTION public.can_access_storage_path(storage_path text)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id text;
  user_role text;
  path_yacht_id uuid;
  root_dir text;
BEGIN
  -- Get current user's yacht_id and role from JWT
  user_yacht_id := auth.jwt()->>'yacht_id';
  user_role := auth.jwt()->>'role';

  -- If no yacht_id in JWT, deny access
  IF user_yacht_id IS NULL THEN
    RETURN false;
  END IF;

  -- Extract yacht_id from storage path
  path_yacht_id := extract_yacht_id_from_storage_path(storage_path);

  -- Yacht isolation: user must match path's yacht
  IF user_yacht_id::uuid != path_yacht_id THEN
    RETURN false;
  END IF;

  -- Extract ROOT directory from path
  root_dir := extract_root_directory_from_storage(storage_path);

  -- Check if user's role has permission to this directory
  RETURN can_role_access_directory(
    path_yacht_id,
    user_role,
    root_dir,
    false  -- Only require read permission
  );
END;
$$;

COMMENT ON FUNCTION public.can_access_storage_path(text) IS
  'Main RLS function for storage.objects. Checks: '
  '1. User yacht_id matches path yacht_id '
  '2. User role has permission to access ROOT directory. '
  'Used by SELECT/UPDATE/DELETE policies on storage.objects.';

-- ----------------------------------------------------------------------------
-- Check if current user can upload to a storage path
-- ----------------------------------------------------------------------------
-- Stricter than read: requires write permission

CREATE OR REPLACE FUNCTION public.can_upload_to_storage_path(storage_path text)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id text;
  user_role text;
  path_yacht_id uuid;
  root_dir text;
BEGIN
  -- Get current user's yacht_id and role from JWT
  user_yacht_id := auth.jwt()->>'yacht_id';
  user_role := auth.jwt()->>'role';

  -- If no yacht_id in JWT, deny access
  IF user_yacht_id IS NULL THEN
    RETURN false;
  END IF;

  -- Validate path format first
  IF NOT validate_storage_path_format(storage_path, 'documents') THEN
    RETURN false;
  END IF;

  -- Extract yacht_id from storage path
  path_yacht_id := extract_yacht_id_from_storage_path(storage_path);

  -- Yacht isolation: user must match path's yacht
  IF user_yacht_id::uuid != path_yacht_id THEN
    RETURN false;
  END IF;

  -- Extract ROOT directory from path
  root_dir := extract_root_directory_from_storage(storage_path);

  -- Check if user's role has WRITE permission to this directory
  RETURN can_role_access_directory(
    path_yacht_id,
    user_role,
    root_dir,
    true  -- Require write permission
  );
END;
$$;

COMMENT ON FUNCTION public.can_upload_to_storage_path(text) IS
  'Upload permission check for storage.objects INSERT policy. '
  'Requires WRITE permission to ROOT directory. '
  'More restrictive than can_access_storage_path (which only requires read).';

-- ----------------------------------------------------------------------------
-- Check if current user can access a document (by document record)
-- ----------------------------------------------------------------------------
-- Used for documents table RLS (alternative to storage path)

CREATE OR REPLACE FUNCTION public.can_access_document(
  doc_yacht_id uuid,
  doc_system_path text
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id text;
  user_role text;
  root_dir text;
BEGIN
  -- Get current user's yacht_id and role from JWT
  user_yacht_id := auth.jwt()->>'yacht_id';
  user_role := auth.jwt()->>'role';

  -- If no yacht_id in JWT, deny access
  IF user_yacht_id IS NULL THEN
    RETURN false;
  END IF;

  -- Yacht isolation
  IF user_yacht_id::uuid != doc_yacht_id THEN
    RETURN false;
  END IF;

  -- Extract ROOT directory from system_path
  root_dir := extract_root_directory(doc_system_path);

  -- Check role permission
  RETURN can_role_access_directory(
    doc_yacht_id,
    user_role,
    root_dir,
    false  -- Only require read permission
  );
END;
$$;

COMMENT ON FUNCTION public.can_access_document(uuid, text) IS
  'Permission check for documents table RLS. '
  'Takes yacht_id and system_path from document record. '
  'Used by SELECT policy on documents table.';

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Build storage path from components
-- ----------------------------------------------------------------------------
-- Helper for Worker 5 (ingestion) to construct valid paths

CREATE OR REPLACE FUNCTION public.build_storage_path(
  p_yacht_id uuid,
  p_system_path text,
  p_filename text,
  p_bucket_id text DEFAULT 'documents'
)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT format(
    '%s/%s/%s/%s',
    p_bucket_id,
    p_yacht_id::text,
    p_system_path,
    p_filename
  );
$$;

COMMENT ON FUNCTION public.build_storage_path(uuid, text, text, text) IS
  'Constructs a valid storage path from components. '
  'Used by Worker 5 during document ingestion. '
  'Example: build_storage_path(yacht_id, "Engineering/Main", "manual.pdf") '
  '→ "documents/yacht_id/Engineering/Main/manual.pdf"';

-- ----------------------------------------------------------------------------
-- List all accessible directories for current user
-- ----------------------------------------------------------------------------
-- Useful for UI to show which folders the user can browse

CREATE OR REPLACE FUNCTION public.get_accessible_directories()
RETURNS TABLE (
  yacht_id uuid,
  root_directory text,
  can_read boolean,
  can_write boolean
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
  user_yacht_id text;
  user_role text;
BEGIN
  -- Get current user's yacht_id and role from JWT
  user_yacht_id := auth.jwt()->>'yacht_id';
  user_role := auth.jwt()->>'role';

  -- If no yacht_id, return empty
  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  -- Return all directories this role can access on this yacht
  RETURN QUERY
  SELECT
    rdp.yacht_id,
    rdp.root_directory,
    rdp.can_read,
    rdp.can_write
  FROM role_directory_permissions rdp
  WHERE rdp.yacht_id = user_yacht_id::uuid
    AND rdp.role_name = user_role
    AND rdp.can_read = true
  ORDER BY rdp.root_directory;
END;
$$;

COMMENT ON FUNCTION public.get_accessible_directories() IS
  'Returns list of ROOT directories current user can access. '
  'Used by frontend to display available folders and permission levels. '
  'Filtered by user yacht_id and role from JWT.';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '✅ Hierarchical storage functions created:';
  RAISE NOTICE '  - extract_yacht_id_from_storage_path()';
  RAISE NOTICE '  - extract_system_path_from_storage()';
  RAISE NOTICE '  - extract_root_directory_from_storage()';
  RAISE NOTICE '  - validate_storage_path_format()';
  RAISE NOTICE '  - assert_valid_yacht_path()';
  RAISE NOTICE '  - can_access_storage_path() ← MAIN RLS FUNCTION';
  RAISE NOTICE '  - can_upload_to_storage_path()';
  RAISE NOTICE '  - can_access_document()';
  RAISE NOTICE '  - build_storage_path()';
  RAISE NOTICE '  - get_accessible_directories()';
END $$;

-- Test basic path parsing
DO $$
DECLARE
  test_path text := 'documents/123e4567-e89b-12d3-a456-426614174000/Engineering/MainEngine/manual.pdf';
  yacht_id_result uuid;
  system_path_result text;
  root_dir_result text;
BEGIN
  yacht_id_result := extract_yacht_id_from_storage_path(test_path);
  system_path_result := extract_system_path_from_storage(test_path);
  root_dir_result := extract_root_directory_from_storage(test_path);

  RAISE NOTICE '🧪 Path parsing test:';
  RAISE NOTICE '  Input: %', test_path;
  RAISE NOTICE '  Yacht ID: %', yacht_id_result;
  RAISE NOTICE '  System path: %', system_path_result;
  RAISE NOTICE '  ROOT directory: %', root_dir_result;

  IF yacht_id_result IS NULL THEN
    RAISE WARNING '⚠️  yacht_id extraction failed';
  END IF;

  IF system_path_result != 'Engineering/MainEngine' THEN
    RAISE WARNING '⚠️  system_path extraction incorrect';
  END IF;

  IF root_dir_result != 'Engineering' THEN
    RAISE WARNING '⚠️  root_directory extraction incorrect';
  END IF;
END $$;
