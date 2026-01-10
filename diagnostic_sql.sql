-- ================================================================================
-- DIAGNOSTIC SCRIPT 1: Database Configuration & Data
-- ================================================================================
-- Run this in Supabase SQL Editor
-- Copy results and share them for diagnosis
-- ================================================================================

-- ================================================================================
-- SECTION 1: RPC Function Configuration
-- ================================================================================
\echo '=== CHECK 1: RPC Function Configuration ==='

SELECT
  '1.1 RPC Function Settings' as check_name,
  proname as function_name,
  prosecdef as has_security_definer,
  proconfig as settings,
  CASE
    WHEN proconfig::text LIKE '%row_security=off%' THEN '✅ row_security is OFF'
    ELSE '❌ row_security NOT disabled - RLS will block queries!'
  END as row_security_status
FROM pg_proc
WHERE proname = 'get_document_storage_path';

SELECT
  '1.2 RPC Function Existence' as check_name,
  routine_name,
  routine_type,
  security_type,
  data_type as return_type
FROM information_schema.routines
WHERE routine_name = 'get_document_storage_path'
  AND routine_schema = 'public';

-- ================================================================================
-- SECTION 2: User & Yacht Assignment
-- ================================================================================
\echo '=== CHECK 2: User Authentication & Yacht Assignment ==='

-- Replace this UUID with your actual user ID from auth.users
-- Get it from: SELECT id FROM auth.users WHERE email = 'x@alex-short.com';
DO $$
DECLARE
  v_user_id UUID := 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';  -- REPLACE THIS
BEGIN
  RAISE NOTICE 'Checking user: %', v_user_id;
END $$;

SELECT
  '2.1 User Profile Check' as check_name,
  id,
  email,
  yacht_id,
  is_active,
  name,
  CASE
    WHEN yacht_id IS NULL THEN '❌ No yacht_id assigned!'
    WHEN is_active = false THEN '❌ User not active!'
    ELSE '✅ User configured correctly'
  END as status
FROM auth_users_profiles
WHERE id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';  -- REPLACE THIS

SELECT
  '2.2 Yacht Details' as check_name,
  y.id as yacht_id,
  y.name as yacht_name,
  y.imo,
  y.mmsi,
  COUNT(dm.id) as total_documents,
  COUNT(sdc.id) as total_chunks
FROM yachts y
LEFT JOIN doc_metadata dm ON y.id = dm.yacht_id
LEFT JOIN search_document_chunks sdc ON y.id = sdc.yacht_id
WHERE y.id = (SELECT yacht_id FROM auth_users_profiles WHERE id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424')
GROUP BY y.id, y.name, y.imo, y.mmsi;

-- ================================================================================
-- SECTION 3: Document Data Verification
-- ================================================================================
\echo '=== CHECK 3: Document Data Exists ==='

-- Get user's yacht_id first
CREATE TEMP TABLE IF NOT EXISTS temp_user_yacht AS
SELECT yacht_id FROM auth_users_profiles WHERE id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

SELECT
  '3.1 search_document_chunks Data' as check_name,
  COUNT(*) as total_chunks,
  COUNT(DISTINCT document_id) as unique_documents,
  COUNT(DISTINCT yacht_id) as yacht_count,
  CASE
    WHEN COUNT(*) = 0 THEN '❌ No chunks found for your yacht!'
    ELSE '✅ Chunks exist'
  END as status
FROM search_document_chunks
WHERE yacht_id = (SELECT yacht_id FROM temp_user_yacht);

-- Show sample chunks
SELECT
  '3.2 Sample Chunks from Your Yacht' as check_name,
  sdc.id as chunk_id,
  sdc.document_id,
  LEFT(sdc.content, 50) as content_preview,
  sdc.yacht_id
FROM search_document_chunks sdc
WHERE sdc.yacht_id = (SELECT yacht_id FROM temp_user_yacht)
LIMIT 5;

SELECT
  '3.3 doc_metadata Data' as check_name,
  COUNT(*) as total_docs,
  COUNT(CASE WHEN storage_path IS NOT NULL THEN 1 END) as docs_with_storage_path,
  COUNT(CASE WHEN storage_path IS NULL THEN 1 END) as docs_without_storage_path,
  CASE
    WHEN COUNT(*) = 0 THEN '❌ No documents in doc_metadata!'
    WHEN COUNT(CASE WHEN storage_path IS NULL THEN 1 END) > 0 THEN '⚠️  Some docs missing storage_path!'
    ELSE '✅ All docs have storage_path'
  END as status
FROM doc_metadata
WHERE yacht_id = (SELECT yacht_id FROM temp_user_yacht);

-- Show sample documents
SELECT
  '3.4 Sample Documents from doc_metadata' as check_name,
  dm.id as document_id,
  dm.filename,
  dm.storage_path,
  CASE
    WHEN dm.storage_path IS NULL THEN '❌ Missing storage_path'
    WHEN dm.storage_path NOT LIKE (SELECT yacht_id::text || '/%' FROM temp_user_yacht) THEN '❌ Path does not start with yacht_id'
    ELSE '✅ Valid path'
  END as path_status
FROM doc_metadata dm
WHERE dm.yacht_id = (SELECT yacht_id FROM temp_user_yacht)
LIMIT 5;

-- ================================================================================
-- SECTION 4: Test Specific Chunk (if you have a failing chunk_id)
-- ================================================================================
\echo '=== CHECK 4: Specific Chunk Verification ==='

-- Replace with actual chunk_id from your error logs
DO $$
DECLARE
  v_test_chunk_id UUID := '0f506cc8-e13c-49e5-bdcb-e3725e8dae1b';  -- REPLACE THIS
BEGIN
  RAISE NOTICE 'Testing chunk_id: %', v_test_chunk_id;
END $$;

SELECT
  '4.1 Chunk Existence & Yacht Match' as check_name,
  sdc.id as chunk_id,
  sdc.document_id,
  sdc.yacht_id as chunk_yacht_id,
  (SELECT yacht_id FROM temp_user_yacht) as user_yacht_id,
  dm.filename,
  dm.storage_path,
  CASE
    WHEN sdc.id IS NULL THEN '❌ Chunk does not exist!'
    WHEN sdc.yacht_id != (SELECT yacht_id FROM temp_user_yacht) THEN '❌ Chunk belongs to different yacht (security blocking)'
    WHEN dm.storage_path IS NULL THEN '❌ Chunk exists but doc_metadata missing storage_path'
    ELSE '✅ Chunk valid and accessible'
  END as diagnosis
FROM search_document_chunks sdc
LEFT JOIN doc_metadata dm ON sdc.document_id = dm.id
WHERE sdc.id = '0f506cc8-e13c-49e5-bdcb-e3725e8dae1b';  -- REPLACE THIS

-- ================================================================================
-- SECTION 5: RLS Policies Verification
-- ================================================================================
\echo '=== CHECK 5: RLS Policies ==='

SELECT
  '5.1 Current RLS Policies' as check_name,
  tablename,
  policyname,
  cmd as command_type,
  CASE
    WHEN qual::text LIKE '%COALESCE%jwt_yacht_id%get_user_yacht_id%' THEN '✅ Has COALESCE fallback'
    WHEN qual::text LIKE '%jwt_yacht_id%' THEN '⚠️  Uses jwt_yacht_id without fallback'
    ELSE '❌ Unknown policy format'
  END as policy_status,
  LEFT(qual::text, 100) as using_clause_preview
FROM pg_policies
WHERE tablename IN ('search_document_chunks', 'doc_metadata')
ORDER BY tablename, policyname;

-- ================================================================================
-- SECTION 6: Helper Functions Check
-- ================================================================================
\echo '=== CHECK 6: Helper Functions ==='

SELECT
  '6.1 Helper Functions Existence' as check_name,
  routine_name,
  routine_type,
  data_type as return_type,
  CASE
    WHEN routine_name = 'jwt_yacht_id' THEN 'Reads yacht_id from JWT'
    WHEN routine_name = 'get_user_yacht_id' THEN 'Queries auth_users_profiles for yacht_id'
    WHEN routine_name = 'get_user_auth_info' THEN 'Gets user profile info'
    ELSE 'Unknown function'
  END as purpose
FROM information_schema.routines
WHERE routine_name IN ('jwt_yacht_id', 'get_user_yacht_id', 'get_user_auth_info')
  AND routine_schema = 'public';

-- ================================================================================
-- SECTION 7: Foreign Key Relationships
-- ================================================================================
\echo '=== CHECK 7: Foreign Key Integrity ==='

SELECT
  '7.1 Orphaned Chunks (no matching doc_metadata)' as check_name,
  COUNT(*) as orphaned_count,
  CASE
    WHEN COUNT(*) > 0 THEN '⚠️  Found chunks without matching documents'
    ELSE '✅ All chunks have matching documents'
  END as status
FROM search_document_chunks sdc
LEFT JOIN doc_metadata dm ON sdc.document_id = dm.id
WHERE dm.id IS NULL
  AND sdc.yacht_id = (SELECT yacht_id FROM temp_user_yacht);

SELECT
  '7.2 Documents without Chunks' as check_name,
  COUNT(*) as docs_without_chunks,
  CASE
    WHEN COUNT(*) > 0 THEN '⚠️  Found documents without chunks (not indexed)'
    ELSE '✅ All documents have chunks'
  END as status
FROM doc_metadata dm
LEFT JOIN search_document_chunks sdc ON dm.id = sdc.document_id
WHERE sdc.id IS NULL
  AND dm.yacht_id = (SELECT yacht_id FROM temp_user_yacht);

-- ================================================================================
-- SECTION 8: Test RPC Function Directly (as current user)
-- ================================================================================
\echo '=== CHECK 8: Test RPC Function ==='

-- This simulates what happens when frontend calls the RPC
-- NOTE: This might fail with auth.uid() = NULL if run in SQL Editor
--       Better to test this in browser console

SELECT '8.1 RPC Test (may fail in SQL Editor - test in browser instead)' as check_name;

-- Get a sample chunk_id to test
SELECT
  '8.2 Sample Chunk for Testing' as check_name,
  id as chunk_id_to_test,
  'Use this in browser console: supabase.rpc("get_document_storage_path", {p_chunk_id: "' || id || '"})' as test_command
FROM search_document_chunks
WHERE yacht_id = (SELECT yacht_id FROM temp_user_yacht)
LIMIT 1;

-- Cleanup
DROP TABLE temp_user_yacht;

-- ================================================================================
-- END OF DIAGNOSTIC
-- ================================================================================
-- Copy ALL results from this script and share for diagnosis
-- ================================================================================
