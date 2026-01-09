-- ================================================================================
-- FIX: Create RPC function to get document storage path
-- ================================================================================
-- Problem: DocumentSituationView queries search_document_chunks directly, but RLS
-- sub-query on auth_users fails, causing "Cannot coerce to single JSON object" error
--
-- Solution: Create SECURITY DEFINER RPC that bypasses the RLS cascade while still
-- validating yacht access
-- ================================================================================

-- Drop if exists (for idempotency)
DROP FUNCTION IF EXISTS get_document_storage_path(UUID);

-- Create RPC function with SECURITY DEFINER
CREATE OR REPLACE FUNCTION get_document_storage_path(p_chunk_id UUID)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  storage_path TEXT,
  yacht_id UUID,
  filename TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_user_id UUID;
  v_user_yacht_id UUID;
BEGIN
  -- Get current user ID from JWT
  v_user_id := auth.uid();

  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- Get user's yacht_id from auth_users (bypasses RLS since SECURITY DEFINER)
  SELECT au.yacht_id INTO v_user_yacht_id
  FROM auth_users au
  WHERE au.auth_user_id = v_user_id
    AND au.is_active = true;

  IF v_user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not assigned to yacht';
  END IF;

  -- Return document info ONLY if chunk belongs to user's yacht
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id;  -- Security: only return if same yacht

  -- If no rows returned, chunk doesn't exist or user doesn't have access
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or access denied';
  END IF;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION get_document_storage_path(UUID) TO authenticated;

-- Add comment
COMMENT ON FUNCTION get_document_storage_path IS
  'Securely retrieves document storage path for a chunk ID. Validates yacht access.';

-- ================================================================================
-- TEST QUERY (run manually to verify)
-- ================================================================================
-- SELECT * FROM get_document_storage_path('your-chunk-id-here'::UUID);
