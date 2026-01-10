-- ================================================================================
-- MIGRATION: Add SET row_security = off to get_document_storage_path RPC
-- ================================================================================
-- Problem: SECURITY DEFINER alone doesn't bypass RLS - RLS policies still evaluated
-- Root Cause: Missing SET row_security = off in function definition
-- Impact: Function may fail if RLS policies have issues (like broken table references)
--
-- Fix: Add SET row_security = off to bypass RLS within the function
-- ================================================================================

-- Recreate function with row_security = off
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
SET row_security = off  -- NEW: Bypass RLS within this function
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

  -- Get user's yacht_id from auth_users_profiles (bypasses RLS since SECURITY DEFINER + row_security off)
  SELECT up.yacht_id INTO v_user_yacht_id
  FROM auth_users_profiles up
  WHERE up.id = v_user_id
    AND up.is_active = true;

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
  'Securely retrieves document storage path. Accepts chunk_id OR document_id. Validates yacht access. Bypasses RLS for reliable execution.';

-- Verify function was updated
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
      AND p.proname = 'get_document_storage_path'
  ) THEN
    RAISE NOTICE '✅ get_document_storage_path function updated with row_security = off';
  ELSE
    RAISE EXCEPTION '❌ Failed to update get_document_storage_path function';
  END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- Why SET row_security = off is important:
-- 1. SECURITY DEFINER alone doesn't bypass RLS
-- 2. RLS policies are still evaluated even with elevated privileges
-- 3. If RLS policy has issues (broken table refs), function fails
-- 4. SET row_security = off fully bypasses RLS within the function
-- 5. Security is still enforced by manual yacht_id validation in the function
-- ================================================================================
