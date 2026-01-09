-- ================================================================================
-- MIGRATION: Fix RLS policies - Add JWT fallback
-- ================================================================================
-- Problem: Document viewing fails with 400 Bad Request
-- Root Cause:
--   - RLS policies use jwt_yacht_id() but JWT doesn't have yacht_id yet
--   - jwt_yacht_id() returns NULL
--   - Policy: yacht_id = NULL → FAILS
--   - RPC get_document_storage_path blocked by RLS
--
-- Solution: Use COALESCE to fallback to DB query if JWT missing yacht_id
-- ================================================================================

-- ================================================================================
-- Update doc_metadata RLS policy
-- ================================================================================

DROP POLICY IF EXISTS "Users can view documents" ON doc_metadata;

CREATE POLICY "Users can view documents" ON doc_metadata
  FOR SELECT
  TO public
  USING (
    yacht_id = COALESCE(
      jwt_yacht_id(),           -- Try JWT first (fast, no DB query)
      get_user_yacht_id()       -- Fallback to DB query (works now)
    )
  );

COMMENT ON POLICY "Users can view documents" ON doc_metadata IS
  'Uses JWT yacht_id if available (fast), falls back to DB query (slower but works)';

-- ================================================================================
-- Update search_document_chunks RLS policy
-- ================================================================================

DROP POLICY IF EXISTS "Users can view document chunks" ON search_document_chunks;

CREATE POLICY "Users can view document chunks" ON search_document_chunks
  FOR SELECT
  TO public
  USING (
    yacht_id = COALESCE(
      jwt_yacht_id(),           -- Try JWT first
      get_user_yacht_id()       -- Fallback to DB query
    )
  );

COMMENT ON POLICY "Users can view document chunks" ON search_document_chunks IS
  'Uses JWT yacht_id if available (fast), falls back to DB query (slower but works)';

-- ================================================================================
-- Why This Works
-- ================================================================================
-- COALESCE returns the first non-NULL value:
--
-- BEFORE JWT HOOK ENABLED:
--   1. jwt_yacht_id() → NULL (JWT doesn't have yacht_id)
--   2. get_user_yacht_id() → "85fe1119..." (queries auth_users_profiles)
--   3. Policy: yacht_id = "85fe1119..." → PASS ✅
--
-- AFTER JWT HOOK ENABLED:
--   1. jwt_yacht_id() → "85fe1119..." (reads from JWT, fast!)
--   2. get_user_yacht_id() → Never called (COALESCE stops at first non-NULL)
--   3. Policy: yacht_id = "85fe1119..." → PASS ✅
--   4. BONUS: 0 database queries (faster!)
--
-- ================================================================================

-- ================================================================================
-- VERIFICATION
-- ================================================================================

-- Check policies were updated
SELECT
  tablename,
  policyname,
  substring(qual::text, 1, 120) as policy_check
FROM pg_policies
WHERE tablename IN ('doc_metadata', 'search_document_chunks')
  AND policyname LIKE 'Users can view%'
ORDER BY tablename;

-- Test RPC works (replace with real user UUID and document UUID)
-- SELECT * FROM get_document_storage_path('98afe6f2-bdda-44e8-ad32-0b412816b860'::uuid);

-- ================================================================================
-- EXPECTED RESULT
-- ================================================================================
-- Policies should show:
--   yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id())
--
-- RPC should return:
--   storage_path, filename, yacht_id (not 400 error)
-- ================================================================================
