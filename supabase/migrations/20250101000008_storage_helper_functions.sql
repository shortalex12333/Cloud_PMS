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
