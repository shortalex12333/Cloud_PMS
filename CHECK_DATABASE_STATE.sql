-- ============================================================================
-- Database State Diagnostic
-- Purpose: Check what's actually deployed in Supabase
-- Run this first to understand your current state
-- ============================================================================

\set QUIET on
\pset border 2
\pset format wrapped

\echo ''
\echo '============================================'
\echo 'SUPABASE DATABASE STATE CHECK'
\echo '============================================'
\echo ''

-- ============================================================================
-- 1. Check if documents table exists
-- ============================================================================

\echo '1. Checking if documents table exists...'
SELECT
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'documents'
    )
    THEN '✅ documents table EXISTS'
    ELSE '❌ documents table DOES NOT EXIST - Run migration 001'
  END AS status;

\echo ''

-- ============================================================================
-- 2. Check documents table columns (if table exists)
-- ============================================================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'documents'
  ) THEN
    RAISE NOTICE '2. Documents table columns:';
  END IF;
END $$;

SELECT
  column_name,
  data_type,
  CASE
    WHEN is_nullable = 'YES' THEN 'NULL'
    ELSE 'NOT NULL'
  END AS nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'documents'
ORDER BY ordinal_position;

\echo ''

-- ============================================================================
-- 3. Check for system_path column specifically
-- ============================================================================

\echo '3. Checking for system_path column...'
SELECT
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'documents'
        AND column_name = 'system_path'
    )
    THEN '✅ system_path column EXISTS'
    ELSE '❌ system_path column MISSING - Need to add it'
  END AS status;

\echo ''

-- ============================================================================
-- 4. Check for storage buckets
-- ============================================================================

\echo '4. Checking storage buckets...'
SELECT
  id AS bucket_name,
  public,
  file_size_limit / 1024 / 1024 AS max_size_mb,
  CASE
    WHEN allowed_mime_types IS NULL THEN 'All types allowed ✅'
    ELSE array_length(allowed_mime_types, 1)::text || ' types restricted ⚠️'
  END AS mime_policy,
  created_at
FROM storage.buckets
WHERE id IN ('documents', 'raw-uploads')
ORDER BY id;

-- Show if no buckets
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id IN ('documents', 'raw-uploads')) THEN
    RAISE NOTICE '❌ No storage buckets found - Run migration 007';
  END IF;
END $$;

\echo ''

-- ============================================================================
-- 5. Check RLS policies on documents table
-- ============================================================================

\echo '5. Checking RLS policies on documents...'

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'documents'
  ) THEN
    RAISE NOTICE 'RLS policies on documents table:';
  END IF;
END $$;

SELECT
  policyname AS policy_name,
  cmd AS operation,
  roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'documents'
ORDER BY cmd, policyname;

-- Show if no policies
DO $$
DECLARE
  policy_count integer;
BEGIN
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'documents';

  IF policy_count = 0 THEN
    RAISE NOTICE '❌ No RLS policies found on documents table - Run migration 002';
  END IF;
END $$;

\echo ''

-- ============================================================================
-- 6. Check helper functions
-- ============================================================================

\echo '6. Checking storage helper functions...'
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'get_yacht_id')
    THEN '✅ get_yacht_id() exists'
    ELSE '❌ get_yacht_id() missing - Run migration 008'
  END AS func1,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'extract_yacht_id_from_path')
    THEN '✅ extract_yacht_id_from_path() exists'
    ELSE '❌ extract_yacht_id_from_path() missing - Run migration 008'
  END AS func2,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'validate_storage_path_format')
    THEN '✅ validate_storage_path_format() exists'
    ELSE '❌ validate_storage_path_format() missing - Run migration 008'
  END AS func3;

\echo ''

-- ============================================================================
-- 7. Summary and Recommendations
-- ============================================================================

\echo '============================================'
\echo 'SUMMARY & RECOMMENDATIONS'
\echo '============================================'
\echo ''

DO $$
DECLARE
  has_documents_table boolean;
  has_system_path boolean;
  has_storage_buckets boolean;
  has_helper_functions boolean;
BEGIN
  -- Check documents table
  SELECT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'documents'
  ) INTO has_documents_table;

  -- Check system_path column
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'documents'
      AND column_name = 'system_path'
  ) INTO has_system_path;

  -- Check storage buckets
  SELECT EXISTS (
    SELECT 1 FROM storage.buckets
    WHERE id = 'documents'
  ) INTO has_storage_buckets;

  -- Check helper functions
  SELECT EXISTS (
    SELECT 1 FROM pg_proc
    WHERE proname = 'get_yacht_id'
  ) INTO has_helper_functions;

  -- Provide recommendations
  RAISE NOTICE 'Current State:';
  RAISE NOTICE '  Documents table: %', CASE WHEN has_documents_table THEN '✅' ELSE '❌' END;
  RAISE NOTICE '  system_path column: %', CASE WHEN has_system_path THEN '✅' ELSE '❌' END;
  RAISE NOTICE '  Storage buckets: %', CASE WHEN has_storage_buckets THEN '✅' ELSE '❌' END;
  RAISE NOTICE '  Helper functions: %', CASE WHEN has_helper_functions THEN '✅' ELSE '❌' END;
  RAISE NOTICE '';

  IF NOT has_documents_table THEN
    RAISE NOTICE '❌ CRITICAL: documents table does not exist';
    RAISE NOTICE '   Action: Run migration 001 (initial_schema_v2.sql) first';
    RAISE NOTICE '';
  END IF;

  IF has_documents_table AND NOT has_system_path THEN
    RAISE NOTICE '⚠️  WARNING: system_path column missing';
    RAISE NOTICE '   Action: Run FIX_ADD_SYSTEM_PATH.sql';
    RAISE NOTICE '';
  END IF;

  IF NOT has_storage_buckets THEN
    RAISE NOTICE '⚠️  WARNING: Storage buckets not created';
    RAISE NOTICE '   Action: Run migration 007 (create_storage_buckets.sql)';
    RAISE NOTICE '';
  END IF;

  IF NOT has_helper_functions THEN
    RAISE NOTICE 'ℹ️  INFO: Helper functions not deployed';
    RAISE NOTICE '   Action: Run migration 008 (storage_helper_functions.sql)';
    RAISE NOTICE '';
  END IF;

  IF has_documents_table AND has_system_path AND has_storage_buckets THEN
    RAISE NOTICE '✅ All critical components present';
    RAISE NOTICE '   You can proceed with Worker 4 testing';
  END IF;

END $$;

\echo ''
\echo '============================================'
\echo 'END OF DIAGNOSTIC'
\echo '============================================'
