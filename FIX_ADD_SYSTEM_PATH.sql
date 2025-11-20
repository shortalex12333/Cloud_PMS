-- ============================================================================
-- Migration: Add system_path to documents (STANDALONE VERSION)
-- Version: 20250101000011_v2
-- Purpose: Add system_path column regardless of current table state
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-11-20
-- ============================================================================
--
-- This version checks for table/column existence before operating
-- Safe to run regardless of current database state
-- ============================================================================

-- ============================================================================
-- STEP 1: Add system_path column (if not exists)
-- ============================================================================

DO $$
BEGIN
  -- Check if documents table exists
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'documents'
  ) THEN

    -- Add system_path column if it doesn't exist
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'documents'
        AND column_name = 'system_path'
    ) THEN
      ALTER TABLE documents ADD COLUMN system_path text;
      RAISE NOTICE '✅ Added system_path column to documents table';
    ELSE
      RAISE NOTICE 'ℹ️  system_path column already exists';
    END IF;

    -- ============================================================================
    -- STEP 2: Backfill system_path from file_path (if file_path exists)
    -- ============================================================================

    -- Check if file_path column exists
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'documents'
        AND column_name = 'file_path'
    ) THEN

      -- Backfill system_path from file_path for existing rows
      -- file_path format: documents/{yacht_id}/{system_path}/{filename}
      UPDATE documents
      SET system_path = regexp_replace(
        file_path,
        '^documents/[^/]+/(.+)/[^/]+$',  -- Extract middle portion
        '\1'
      )
      WHERE system_path IS NULL
        AND file_path ~ '^documents/[^/]+/.+/[^/]+$';

      RAISE NOTICE '✅ Backfilled system_path from file_path';

    ELSE
      RAISE NOTICE 'ℹ️  file_path column does not exist - skipping backfill';
    END IF;

    -- ============================================================================
    -- STEP 3: Make system_path NOT NULL (optional - skip if no data)
    -- ============================================================================

    -- Only set NOT NULL if all rows have system_path
    DECLARE
      null_count integer;
    BEGIN
      SELECT COUNT(*) INTO null_count
      FROM documents
      WHERE system_path IS NULL;

      IF null_count = 0 THEN
        ALTER TABLE documents ALTER COLUMN system_path SET NOT NULL;
        RAISE NOTICE '✅ Set system_path to NOT NULL';
      ELSE
        RAISE NOTICE 'ℹ️  Skipping NOT NULL constraint (% rows have NULL system_path)', null_count;
      END IF;
    END;

    -- ============================================================================
    -- STEP 4: Add indexes
    -- ============================================================================

    -- Index for queries like "find all Engineering documents for yacht X"
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'public'
        AND tablename = 'documents'
        AND indexname = 'idx_documents_yacht_system_path'
    ) THEN
      CREATE INDEX idx_documents_yacht_system_path
      ON documents (yacht_id, system_path);
      RAISE NOTICE '✅ Created index: idx_documents_yacht_system_path';
    END IF;

    -- Enable trigram extension if not already enabled
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- GIN index for pattern matching on system_path
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'public'
        AND tablename = 'documents'
        AND indexname = 'idx_documents_system_path_gin'
    ) THEN
      CREATE INDEX idx_documents_system_path_gin
      ON documents USING gin (system_path gin_trgm_ops);
      RAISE NOTICE '✅ Created GIN index: idx_documents_system_path_gin';
    END IF;

    -- Index for root directory queries
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'public'
        AND tablename = 'documents'
        AND indexname = 'idx_documents_root_directory'
    ) THEN
      CREATE INDEX idx_documents_root_directory
      ON documents ((split_part(system_path, '/', 1)), yacht_id);
      RAISE NOTICE '✅ Created index: idx_documents_root_directory';
    END IF;

    -- ============================================================================
    -- STEP 5: Add comment
    -- ============================================================================

    COMMENT ON COLUMN documents.system_path IS
      'Hierarchical path from yacht NAS (e.g., "03_Engineering/MainEngine"). '
      'Dynamically detected from yacht folder structure. Used for directory-based permissions.';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ Migration Complete';
    RAISE NOTICE '========================================';

  ELSE
    RAISE EXCEPTION 'documents table does not exist. Run migration 001 first.';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  has_column boolean;
  row_count integer;
  null_count integer;
BEGIN
  -- Check if column was added
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'documents'
      AND column_name = 'system_path'
  ) INTO has_column;

  IF has_column THEN
    -- Get stats
    SELECT COUNT(*) INTO row_count FROM documents;
    SELECT COUNT(*) INTO null_count FROM documents WHERE system_path IS NULL;

    RAISE NOTICE '';
    RAISE NOTICE 'Verification Results:';
    RAISE NOTICE '  Column exists: ✅';
    RAISE NOTICE '  Total documents: %', row_count;
    RAISE NOTICE '  Documents with system_path: %', row_count - null_count;
    RAISE NOTICE '  Documents without system_path: %', null_count;
    RAISE NOTICE '';

    IF row_count > 0 AND null_count > 0 THEN
      RAISE NOTICE '⚠️  Warning: Some documents do not have system_path set.';
      RAISE NOTICE '   This is OK if those documents were uploaded before this migration.';
      RAISE NOTICE '   New uploads MUST include system_path.';
    END IF;

  ELSE
    RAISE EXCEPTION 'system_path column was not created!';
  END IF;
END $$;
