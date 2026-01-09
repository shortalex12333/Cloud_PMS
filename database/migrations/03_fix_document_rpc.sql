-- ================================================================================
-- FIX: Create RPC function to get document storage path
-- ================================================================================
-- Problem: DocumentSituationView queries search_document_chunks directly, but RLS
-- sub-query on auth_users fails, causing "Cannot coerce to single JSON object" error
--
-- Solution: Create SECURITY DEFINER RPC that bypasses the RLS cascade while still
-- validating yacht access
--
-- UPDATE: Now accepts EITHER chunk_id OR document_id (backend may return either)
-- ================================================================================

-- Drop if exists (for idempotency)
DROP FUNCTION IF EXISTS get_document_storage_path(UUID);

-- Create RPC function with SECURITY DEFINER
-- Accepts p_chunk_id which can be EITHER a chunk UUID or document UUID
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
  v_found BOOLEAN := FALSE;
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

  -- STRATEGY 1: Try as chunk_id first (most specific)
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
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- STRATEGY 2: Try as document_id (backend might return document UUID)
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.document_id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id
  LIMIT 1;  -- Just need one chunk to get storage_path

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- STRATEGY 3: Try as doc_metadata.id directly (no chunks)
  RETURN QUERY
  SELECT
    NULL::UUID as chunk_id,
    dm.id as document_id,
    dm.storage_path,
    dm.yacht_id,
    dm.filename
  FROM doc_metadata dm
  WHERE dm.id = p_chunk_id
    AND dm.yacht_id = v_user_yacht_id;

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- Nothing found - document doesn't exist or user doesn't have access
  IF NOT v_found THEN
    RAISE EXCEPTION 'Document not found or access denied';
  END IF;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION get_document_storage_path(UUID) TO authenticated;

-- Add comment
COMMENT ON FUNCTION get_document_storage_path IS
  'Securely retrieves document storage path. Accepts chunk_id OR document_id. Validates yacht access.';

-- ================================================================================
-- TEST QUERIES (run manually to verify)
-- ================================================================================
-- By chunk_id:
-- SELECT * FROM get_document_storage_path('0f506cc8-e13c-49e5-bdcb-e3725e8dae1b'::UUID);
-- By document_id:
-- SELECT * FROM get_document_storage_path('2a1ede18-4293-47f3-a4c0-5ab96001691b'::UUID);
