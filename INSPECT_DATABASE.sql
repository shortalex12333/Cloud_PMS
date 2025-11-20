-- ============================================================================
-- COMPREHENSIVE DATABASE INSPECTION QUERY
-- ============================================================================
-- Copy this entire file and run it in Supabase SQL Editor
-- It will show exactly what's deployed and what's missing
-- ============================================================================

\echo '========================================='
\echo 'CELESTEOS DATABASE INSPECTION REPORT'
\echo '========================================='
\echo ''

-- ============================================================================
-- 1. PGVECTOR EXTENSION
-- ============================================================================
\echo '[1/15] Checking pgvector extension...'
SELECT
  CASE
    WHEN COUNT(*) = 1 THEN '✅ pgvector ENABLED (version: ' || extversion || ')'
    ELSE '❌ pgvector NOT ENABLED - Need migration 000'
  END as status
FROM pg_extension
WHERE extname = 'vector';

\echo ''

-- ============================================================================
-- 2. TABLES COUNT
-- ============================================================================
\echo '[2/15] Checking tables...'
SELECT
  CASE
    WHEN COUNT(*) >= 34 THEN '✅ All tables exist (' || COUNT(*) || ' tables)'
    WHEN COUNT(*) = 0 THEN '❌ NO TABLES - Need migration 001'
    ELSE '⚠️  Partial deployment (' || COUNT(*) || '/34 tables) - Need migration 001'
  END as status
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- List all tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

\echo ''

-- ============================================================================
-- 3. CRITICAL TABLES CHECK
-- ============================================================================
\echo '[3/15] Checking critical tables...'
SELECT
  'yachts' as table_name,
  CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'yachts') THEN '✅' ELSE '❌' END as exists
UNION ALL SELECT 'users', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'agents', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'agents') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'api_keys', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'api_keys') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'documents', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'documents') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'document_chunks', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_chunks') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'equipment', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'equipment') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'work_orders', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'work_orders') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'parts', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'parts') THEN '✅' ELSE '❌' END
UNION ALL SELECT 'user_roles', CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_roles') THEN '✅' ELSE '❌' END;

\echo ''

-- ============================================================================
-- 4. VECTOR DIMENSION (CRITICAL!)
-- ============================================================================
\echo '[4/15] Checking vector dimension (CRITICAL)...'
SELECT
  CASE
    WHEN column_name IS NULL THEN '❌ document_chunks table NOT FOUND - Need migration 001'
    WHEN data_type LIKE '%1536%' OR udt_name LIKE '%1536%' THEN '✅ vector(1536) CORRECT - OpenAI compatible'
    ELSE '❌ WRONG DIMENSION (should be 1536, not 1024) - Need to redeploy migration 001'
  END as status,
  COALESCE(udt_name, 'N/A') as current_type
FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding'
UNION ALL
SELECT '⚠️  If wrong dimension, run fix_vector_dimension.sql', '';

\echo ''

-- ============================================================================
-- 5. RLS ENABLED
-- ============================================================================
\echo '[5/15] Checking RLS enabled...'
SELECT
  CASE
    WHEN COUNT(DISTINCT c.relname) >= 34 THEN '✅ RLS enabled on all tables (' || COUNT(DISTINCT c.relname) || ' tables)'
    WHEN COUNT(DISTINCT c.relname) = 0 THEN '❌ RLS NOT ENABLED - Need migration 002'
    ELSE '⚠️  Partial RLS (' || COUNT(DISTINCT c.relname) || '/34 tables) - Need migration 002'
  END as status
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relrowsecurity = true;

\echo ''

-- ============================================================================
-- 6. RLS POLICIES COUNT
-- ============================================================================
\echo '[6/15] Checking RLS policies...'
SELECT
  CASE
    WHEN COUNT(*) >= 50 THEN '✅ All RLS policies deployed (' || COUNT(*) || ' policies)'
    WHEN COUNT(*) = 0 THEN '❌ NO RLS POLICIES - Need migration 002'
    ELSE '⚠️  Partial RLS policies (' || COUNT(*) || '/50+) - Need migration 002'
  END as status
FROM pg_policies
WHERE schemaname = 'public';

-- Show policy count per table
SELECT
  tablename,
  COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename
LIMIT 10;

\echo ''

-- ============================================================================
-- 7. HELPER FUNCTIONS
-- ============================================================================
\echo '[7/15] Checking helper functions...'
SELECT
  CASE
    WHEN COUNT(*) >= 3 THEN '✅ RLS helper functions exist'
    ELSE '❌ RLS helper functions missing - Need migration 002'
  END as status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('get_user_yacht_id', 'get_user_role', 'is_manager');

\echo ''

-- ============================================================================
-- 8. SEARCH FUNCTIONS
-- ============================================================================
\echo '[8/15] Checking search functions...'
SELECT
  routine_name,
  CASE WHEN routine_name IS NOT NULL THEN '✅' ELSE '❌' END as exists
FROM (
  VALUES
    ('match_documents'),
    ('search_documents_advanced'),
    ('hybrid_search'),
    ('get_similar_chunks')
) AS expected(routine_name)
LEFT JOIN information_schema.routines r
  ON r.routine_schema = 'public' AND r.routine_name = expected.routine_name;

SELECT
  CASE
    WHEN COUNT(*) >= 4 THEN '✅ All search functions exist'
    WHEN COUNT(*) = 0 THEN '❌ NO SEARCH FUNCTIONS - Need migration 003'
    ELSE '⚠️  Partial search functions - Need migration 003'
  END as status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('match_documents', 'search_documents_advanced', 'hybrid_search', 'get_similar_chunks');

\echo ''

-- ============================================================================
-- 9. SEED DATA (USER ROLES)
-- ============================================================================
\echo '[9/15] Checking seed data...'
SELECT
  CASE
    WHEN COUNT(*) = 7 THEN '✅ All 7 user roles seeded'
    WHEN COUNT(*) = 0 THEN '❌ NO SEED DATA - Need migration 004'
    ELSE '⚠️  Partial seed data (' || COUNT(*) || '/7 roles) - Need migration 004'
  END as status
FROM user_roles;

-- List roles
SELECT role_name, display_name
FROM user_roles
ORDER BY role_name;

\echo ''

-- ============================================================================
-- 10. TRIGGERS
-- ============================================================================
\echo '[10/15] Checking triggers...'
SELECT
  CASE
    WHEN COUNT(*) >= 20 THEN '✅ All triggers created (' || COUNT(*) || ' triggers)'
    WHEN COUNT(*) = 0 THEN '❌ NO TRIGGERS - Need migration 005'
    ELSE '⚠️  Partial triggers (' || COUNT(*) || '/20+) - Need migration 005'
  END as status
FROM information_schema.triggers
WHERE trigger_schema = 'public' AND trigger_name NOT LIKE 'pg_%';

-- Critical triggers check
SELECT
  trigger_name,
  event_object_table as table_name
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN ('on_auth_user_created', 'set_updated_at', 'audit_log', 'validate_status', 'on_document_inserted')
ORDER BY trigger_name
LIMIT 10;

\echo ''

-- ============================================================================
-- 11. BUSINESS FUNCTIONS
-- ============================================================================
\echo '[11/15] Checking business functions...'
SELECT
  routine_name,
  CASE WHEN routine_name IS NOT NULL THEN '✅' ELSE '❌' END as exists
FROM (
  VALUES
    ('create_work_order'),
    ('update_work_order_status'),
    ('adjust_inventory_stock'),
    ('get_equipment_health'),
    ('get_yacht_stats'),
    ('traverse_graph')
) AS expected(routine_name)
LEFT JOIN information_schema.routines r
  ON r.routine_schema = 'public' AND r.routine_name = expected.routine_name;

SELECT
  CASE
    WHEN COUNT(*) >= 6 THEN '✅ All business functions exist'
    WHEN COUNT(*) = 0 THEN '❌ NO BUSINESS FUNCTIONS - Need migration 006'
    ELSE '⚠️  Partial business functions - Need migration 006'
  END as status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('create_work_order', 'update_work_order_status', 'adjust_inventory_stock', 'get_equipment_health', 'get_yacht_stats', 'traverse_graph');

\echo ''

-- ============================================================================
-- 12. STORAGE BUCKETS
-- ============================================================================
\echo '[12/15] Checking storage buckets...'
SELECT
  CASE
    WHEN COUNT(*) = 2 THEN '✅ Both storage buckets exist'
    WHEN COUNT(*) = 0 THEN '❌ NO STORAGE BUCKETS - Need migration 007'
    ELSE '⚠️  Partial storage buckets (' || COUNT(*) || '/2) - Need migration 007'
  END as status
FROM storage.buckets
WHERE id IN ('documents', 'raw-uploads');

-- List buckets
SELECT id, name, public, file_size_limit
FROM storage.buckets
WHERE id IN ('documents', 'raw-uploads');

\echo ''

-- ============================================================================
-- 13. STORAGE HELPER FUNCTIONS
-- ============================================================================
\echo '[13/15] Checking storage helper functions...'
SELECT
  routine_name,
  CASE WHEN routine_name IS NOT NULL THEN '✅' ELSE '❌' END as exists
FROM (
  VALUES
    ('get_yacht_id'),
    ('extract_yacht_id_from_path'),
    ('can_access_document'),
    ('assert_valid_yacht_path'),
    ('validate_storage_path_format')
) AS expected(routine_name)
LEFT JOIN information_schema.routines r
  ON r.routine_schema = 'public' AND r.routine_name = expected.routine_name;

SELECT
  CASE
    WHEN COUNT(*) >= 5 THEN '✅ All storage helper functions exist'
    WHEN COUNT(*) = 0 THEN '❌ NO STORAGE HELPERS - Need migration 008'
    ELSE '⚠️  Partial storage helpers - Need migration 008'
  END as status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('get_yacht_id', 'extract_yacht_id_from_path', 'can_access_document', 'assert_valid_yacht_path', 'validate_storage_path_format');

\echo ''

-- ============================================================================
-- 14. STORAGE RLS
-- ============================================================================
\echo '[14/15] Checking storage RLS...'
SELECT
  CASE
    WHEN COUNT(*) >= 5 THEN '✅ Storage RLS policies exist (' || COUNT(*) || ' policies)'
    WHEN COUNT(*) = 0 THEN '❌ NO STORAGE RLS - Need migration 009'
    ELSE '⚠️  Partial storage RLS - Need migration 009'
  END as status
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects';

-- List storage policies
SELECT policyname, cmd as operation
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
ORDER BY policyname;

\echo ''

-- ============================================================================
-- 15. DOCUMENTS METADATA RLS
-- ============================================================================
\echo '[15/15] Checking documents metadata RLS...'
SELECT
  policyname,
  CASE WHEN policyname LIKE '%service%' THEN '✅' ELSE '📋' END as service_role
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'documents'
ORDER BY policyname;

\echo ''
\echo '========================================='
\echo 'SUMMARY'
\echo '========================================='

-- Final summary
SELECT
  '✅ COMPLETE' as status
WHERE
  -- Check all conditions
  EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
  AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') >= 34
  AND (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public') >= 50
  AND (SELECT COUNT(*) FROM user_roles) = 7
  AND (SELECT COUNT(*) FROM storage.buckets WHERE id IN ('documents', 'raw-uploads')) = 2
UNION ALL
SELECT '❌ INCOMPLETE - Check items above' as status
WHERE NOT EXISTS (
  SELECT 1 WHERE
    EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
    AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') >= 34
    AND (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public') >= 50
    AND (SELECT COUNT(*) FROM user_roles) = 7
    AND (SELECT COUNT(*) FROM storage.buckets WHERE id IN ('documents', 'raw-uploads')) = 2
);

\echo ''
\echo 'If status is ❌ INCOMPLETE, run: DEPLOY_ALL_MIGRATIONS.sh'
\echo 'Or copy migrations to Supabase SQL Editor one by one'
\echo ''
