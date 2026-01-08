-- ================================================================================
-- COMPREHENSIVE RLS AND FUNCTION CHECK
-- Find all references to non-existent "users" table
-- ================================================================================

-- CHECK 1: All RLS policies on auth_users table (critical - get_user_yacht_id queries this)
SELECT
  schemaname,
  tablename,
  policyname,
  cmd,
  qual::text as using_expression,
  with_check::text as with_check_expression
FROM pg_policies
WHERE tablename = 'auth_users'
ORDER BY policyname;

-- CHECK 2: All functions that might reference "users" table
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as function_definition
FROM pg_proc
WHERE pg_get_functiondef(oid) ILIKE '%users%'
  AND proname NOT LIKE 'pg_%'
  AND proname NOT LIKE 'auth.%'
ORDER BY proname;

-- CHECK 3: All triggers on search_document_chunks
SELECT
  tgname as trigger_name,
  tgtype,
  proname as function_name,
  pg_get_functiondef(p.oid) as trigger_function_definition
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE c.relname = 'search_document_chunks'
  AND tgname NOT LIKE 'pg_%';

-- CHECK 4: All triggers on auth_users (might interfere)
SELECT
  tgname as trigger_name,
  tgtype,
  proname as function_name,
  pg_get_functiondef(p.oid) as trigger_function_definition
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE c.relname = 'auth_users'
  AND tgname NOT LIKE 'pg_%';

-- CHECK 5: All RLS policies on doc_metadata (we query this next)
SELECT
  schemaname,
  tablename,
  policyname,
  cmd,
  qual::text as using_expression,
  with_check::text as with_check_expression
FROM pg_policies
WHERE tablename = 'doc_metadata'
ORDER BY policyname;

-- CHECK 6: Search for ANY table that has "users" in RLS policy
SELECT
  tablename,
  policyname,
  qual::text as using_expression
FROM pg_policies
WHERE qual::text ILIKE '%users%'
  AND qual::text NOT ILIKE '%auth_users%'
ORDER BY tablename, policyname;

-- ================================================================================
-- PRIORITY CHECKS:
-- 1. auth_users RLS - Most likely culprit (get_user_yacht_id queries this)
-- 2. Functions referencing "users" - Find broken functions
-- 3. Triggers - Might call broken functions
-- 4. Other policies with "users" - Other tables in query chain
-- ================================================================================
