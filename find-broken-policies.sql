-- ================================================================================
-- FIND POLICIES REFERENCING "users" TABLE (NOT "auth_users")
-- ================================================================================

-- Simpler version that avoids aggregate function issues
SELECT
  tablename,
  policyname,
  qual::text as using_expression,
  CASE
    WHEN qual::text LIKE '%from users%' THEN '⚠️ BROKEN: References "users" table'
    WHEN qual::text LIKE '%FROM users%' THEN '⚠️ BROKEN: References "users" table'
    WHEN qual::text LIKE '% users.%' THEN '⚠️ BROKEN: References "users" table'
    WHEN qual::text LIKE '% users %' THEN '⚠️ BROKEN: References "users" table'
    ELSE '✅ OK'
  END as status
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ================================================================================
-- Alternative: Check specific tables in the document loading chain
-- ================================================================================

-- Tables involved in document loading:
-- 1. search_document_chunks (checked ✅)
-- 2. auth_users (checked ✅)
-- 3. doc_metadata (need to check)

SELECT
  tablename,
  policyname,
  qual::text as using_expression
FROM pg_policies
WHERE tablename IN ('search_document_chunks', 'auth_users', 'doc_metadata')
ORDER BY tablename, policyname;
