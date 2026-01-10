-- ================================================================================
-- MIGRATION: Fix search_document_chunks RLS Policy Table Reference
-- ================================================================================
-- Problem: RLS policy references "auth_users" table (doesn't exist - renamed to auth_users_profiles)
-- Root Cause: Migration 05 renamed tables but didn't update this RLS policy
-- Impact: RLS policy fails to evaluate correctly, may block access
--
-- Fix: Update RLS policy to reference auth_users_profiles
-- ================================================================================

-- Drop the broken policy
DROP POLICY IF EXISTS "chunks_yacht_isolation" ON public.search_document_chunks;

-- Create corrected policy using auth_users_profiles
CREATE POLICY "chunks_yacht_isolation"
ON public.search_document_chunks
FOR SELECT
TO authenticated, anon
USING (
  yacht_id IN (
    SELECT yacht_id
    FROM public.auth_users_profiles
    WHERE id = auth.uid()
  )
);

COMMENT ON POLICY "chunks_yacht_isolation" ON public.search_document_chunks IS
  'Enforce yacht isolation - users can only see document chunks for their assigned yachts';

-- Verify policy was created
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'search_document_chunks'
      AND policyname = 'chunks_yacht_isolation'
  ) THEN
    RAISE NOTICE '✅ search_document_chunks RLS policy updated successfully';
  ELSE
    RAISE EXCEPTION '❌ Failed to update search_document_chunks RLS policy';
  END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This policy ensures users can only see document chunks for their yacht
-- Previously referenced "auth_users" table (deleted in migration 05)
-- Now correctly references "auth_users_profiles" table
-- ================================================================================
