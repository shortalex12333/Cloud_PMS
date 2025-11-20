-- ============================================================================
-- CelesteOS Database Verification Script
-- Run this AFTER all migrations are deployed
-- ============================================================================

-- ============================================================================
-- SECTION 1: EXTENSION VERIFICATION
-- ============================================================================

\echo '========================================='
\echo 'SECTION 1: Extension Verification'
\echo '========================================='

-- Check pgvector extension
SELECT
  'pgvector Extension' AS check_name,
  CASE
    WHEN COUNT(*) = 1 THEN '✅ PASS'
    ELSE '❌ FAIL'
  END AS status,
  extversion AS version
FROM pg_extension
WHERE extname = 'vector'
GROUP BY extversion;

-- ============================================================================
-- SECTION 2: TABLE VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 2: Table Count'
\echo '========================================='

SELECT
  'Total Tables' AS check_name,
  CASE
    WHEN COUNT(*) = 34 THEN '✅ PASS (34 tables)'
    ELSE '❌ FAIL (' || COUNT(*) || ' tables, expected 34)'
  END AS status
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- List all tables
\echo ''
\echo 'All Tables:'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- ============================================================================
-- SECTION 3: VECTOR DIMENSION VERIFICATION (CRITICAL!)
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 3: Vector Dimension (CRITICAL)'
\echo '========================================='

SELECT
  'Vector Dimension' AS check_name,
  CASE
    WHEN column_name IS NOT NULL THEN
      CASE
        -- Check if it's vector(1536)
        WHEN data_type LIKE '%1536%' OR udt_name LIKE '%1536%' THEN '✅ PASS (vector(1536) - OpenAI compatible)'
        ELSE '❌ FAIL (Wrong dimension! Should be 1536)'
      END
    ELSE '❌ FAIL (embedding column not found)'
  END AS status
FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding';

-- Detailed column info
SELECT
  table_name,
  column_name,
  data_type,
  udt_name
FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding';

-- ============================================================================
-- SECTION 4: INDEX VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 4: Critical Indexes'
\echo '========================================='

-- Check critical indexes exist
SELECT
  'idx_document_chunks_embedding' AS index_name,
  CASE
    WHEN COUNT(*) = 1 THEN '✅ PASS (IVFFlat vector index exists)'
    ELSE '❌ FAIL (Vector index missing!)'
  END AS status
FROM pg_indexes
WHERE tablename = 'document_chunks' AND indexname = 'idx_document_chunks_embedding';

SELECT
  'idx_users_auth_user_id' AS index_name,
  CASE
    WHEN COUNT(*) = 1 THEN '✅ PASS (Auth integration index exists)'
    ELSE '❌ FAIL (Auth index missing!)'
  END AS status
FROM pg_indexes
WHERE tablename = 'users' AND indexname = 'idx_users_auth_user_id';

-- Count all indexes
SELECT
  'Total Indexes' AS check_name,
  CASE
    WHEN COUNT(*) >= 100 THEN '✅ PASS (' || COUNT(*) || ' indexes)'
    ELSE '⚠️  WARNING (' || COUNT(*) || ' indexes, expected 100+)'
  END AS status
FROM pg_indexes
WHERE schemaname = 'public' AND indexname LIKE 'idx_%';

-- ============================================================================
-- SECTION 5: RLS POLICY VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 5: RLS Policies'
\echo '========================================='

-- Check RLS is enabled on all tables
SELECT
  'RLS Enabled on All Tables' AS check_name,
  CASE
    WHEN COUNT(DISTINCT c.relname) = 34 THEN '✅ PASS (All 34 tables have RLS)'
    ELSE '❌ FAIL (Only ' || COUNT(DISTINCT c.relname) || '/34 tables have RLS)'
  END AS status
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relrowsecurity = true;

-- Count policies
SELECT
  'Total RLS Policies' AS check_name,
  CASE
    WHEN COUNT(*) >= 50 THEN '✅ PASS (' || COUNT(*) || ' policies)'
    ELSE '❌ FAIL (' || COUNT(*) || ' policies, expected 50+)'
  END AS status
FROM pg_policies
WHERE schemaname = 'public';

-- Policy coverage per table
\echo ''
\echo 'RLS Policy Coverage:'
SELECT
  tablename,
  COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

-- ============================================================================
-- SECTION 6: FUNCTION VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 6: Functions'
\echo '========================================='

-- Check critical functions exist
WITH expected_functions AS (
  SELECT unnest(ARRAY[
    'get_user_yacht_id',
    'get_user_role',
    'is_manager',
    'match_documents',
    'search_documents_advanced',
    'hybrid_search',
    'create_work_order',
    'update_work_order_status',
    'adjust_inventory_stock',
    'get_equipment_health',
    'get_yacht_stats',
    'traverse_graph'
  ]) AS func_name
)
SELECT
  ef.func_name,
  CASE
    WHEN r.routine_name IS NOT NULL THEN '✅ EXISTS'
    ELSE '❌ MISSING'
  END AS status
FROM expected_functions ef
LEFT JOIN information_schema.routines r
  ON r.routine_name = ef.func_name
  AND r.routine_schema = 'public'
ORDER BY ef.func_name;

-- ============================================================================
-- SECTION 7: TRIGGER VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 7: Triggers'
\echo '========================================='

SELECT
  'Total Triggers' AS check_name,
  CASE
    WHEN COUNT(*) >= 20 THEN '✅ PASS (' || COUNT(*) || ' triggers)'
    ELSE '⚠️  WARNING (' || COUNT(*) || ' triggers, expected 20+)'
  END AS status
FROM information_schema.triggers
WHERE trigger_schema = 'public' AND trigger_name NOT LIKE 'pg_%';

-- Critical triggers
\echo ''
\echo 'Critical Triggers:'
SELECT
  event_object_table AS table_name,
  trigger_name,
  action_timing || ' ' || string_agg(event_manipulation, ', ') AS trigger_type
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN (
    'on_auth_user_created',
    'set_updated_at',
    'audit_log',
    'on_document_inserted',
    'on_job_completed'
  )
GROUP BY event_object_table, trigger_name, action_timing
ORDER BY event_object_table, trigger_name;

-- ============================================================================
-- SECTION 8: SEED DATA VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 8: Seed Data'
\echo '========================================='

SELECT
  'User Roles Seeded' AS check_name,
  CASE
    WHEN COUNT(*) = 7 THEN '✅ PASS (7 roles)'
    ELSE '❌ FAIL (' || COUNT(*) || ' roles, expected 7)'
  END AS status
FROM user_roles;

-- List all roles
\echo ''
\echo 'User Roles:'
SELECT role_name, display_name FROM user_roles ORDER BY role_name;

-- ============================================================================
-- SECTION 9: FOREIGN KEY VERIFICATION
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 9: Foreign Key Constraints'
\echo '========================================='

SELECT
  'Total Foreign Keys' AS check_name,
  COUNT(*) || ' constraints' AS status
FROM information_schema.table_constraints
WHERE constraint_schema = 'public'
  AND constraint_type = 'FOREIGN KEY';

-- Critical foreign keys
\echo ''
\echo 'Critical Foreign Keys:'
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table,
  ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.constraint_schema = 'public'
  AND kcu.column_name IN ('yacht_id', 'auth_user_id', 'document_id')
ORDER BY tc.table_name, kcu.column_name;

-- ============================================================================
-- SECTION 10: VECTOR OPERATIONS TEST
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'SECTION 10: Vector Operations Test'
\echo '========================================='

-- Test creating a test vector
DO $$
DECLARE
  test_embedding vector(1536);
BEGIN
  -- Create a test 1536-dimension vector
  SELECT array_agg((random() * 2 - 1)::float4)::vector(1536)
  INTO test_embedding
  FROM generate_series(1, 1536);

  RAISE NOTICE '✅ Vector creation successful: % dimensions', array_length(test_embedding::float4[], 1);

  -- Test cosine distance operator
  SELECT test_embedding <=> test_embedding INTO STRICT test_embedding;
  RAISE NOTICE '✅ Cosine distance operator works (self-distance: %)', test_embedding;

EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '❌ Vector operations FAILED: %', SQLERRM;
END $$;

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'FINAL SUMMARY'
\echo '========================================='

SELECT
  'Database Status' AS component,
  '✅ READY FOR PRODUCTION' AS status
WHERE (
  -- All checks must pass
  (SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector') = 1
  AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') = 34
  AND (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public') >= 50
  AND (SELECT COUNT(*) FROM user_roles) = 7
  AND (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'match_documents') = 1
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'document_chunks' AND column_name = 'embedding')
);

\echo ''
\echo '========================================='
\echo 'Verification Complete!'
\echo '========================================='
\echo ''
\echo 'Next steps:'
\echo '1. Create a test yacht'
\echo '2. Create a test user via Supabase Auth'
\echo '3. Test document upload and indexing'
\echo '4. Configure n8n workflow'
\echo ''
