-- ================================================================================
-- FIX SPECIFIC RLS POLICY ON search_document_chunks
-- ================================================================================

-- STEP 1: Check the "Users can view document chunks" policy
-- This is likely the broken one
SELECT
  policyname,
  cmd,
  qual::text as using_expression,
  with_check::text as with_check_expression
FROM pg_policies
WHERE tablename = 'search_document_chunks'
  AND policyname = 'Users can view document chunks';

-- STEP 2: Drop the broken policy
DROP POLICY IF EXISTS "Users can view document chunks" ON search_document_chunks;

-- STEP 3: Create corrected policy
CREATE POLICY "Users can view document chunks"
ON search_document_chunks
FOR SELECT
TO authenticated, anon
USING (
  yacht_id IN (
    SELECT yacht_id
    FROM auth_users
    WHERE auth_user_id = auth.uid()
  )
);

-- STEP 4: Verify the fix
SELECT
  policyname,
  cmd,
  qual::text as using_expression
FROM pg_policies
WHERE tablename = 'search_document_chunks'
  AND policyname = 'Users can view document chunks';

-- ================================================================================
-- EXPECTED RESULT:
-- using_expression should contain:
-- "...SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()..."
-- (NOT "...FROM users WHERE id = auth.uid()...")
-- ================================================================================
