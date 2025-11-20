-- Migration: Add system_path for hierarchical storage
-- Purpose: Support dynamic yacht NAS folder structure preservation
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-01-01

-- ============================================================================
-- ADD SYSTEM_PATH COLUMN
-- ============================================================================
-- Stores the hierarchical path from yacht's NAS
-- Example: "03_Engineering/MainEngine" or "Bridge/Charts"
-- This preserves the yacht's actual folder structure (no forced conventions)

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS system_path text;

-- For existing rows, extract system_path from file_path
-- file_path format: documents/{yacht_id}/{system_path}/{filename}
UPDATE documents
SET system_path = regexp_replace(
  file_path,
  '^documents/[^/]+/(.+)/[^/]+$',  -- Extract middle portion
  '\1'
)
WHERE system_path IS NULL
  AND file_path ~ '^documents/[^/]+/.+/[^/]+$';

-- Now make it NOT NULL (after backfilling existing data)
ALTER TABLE documents
ALTER COLUMN system_path SET NOT NULL;

-- Add comment
COMMENT ON COLUMN documents.system_path IS
  'Hierarchical path from yacht NAS (e.g., "03_Engineering/MainEngine"). '
  'Dynamically detected from yacht folder structure. Used for directory-based permissions.';

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Index for queries like "find all Engineering documents for yacht X"
CREATE INDEX IF NOT EXISTS idx_documents_yacht_system_path
ON documents (yacht_id, system_path);

-- Index for queries like "find all documents in MainEngine folder"
-- Using GIN index for pattern matching on system_path
CREATE INDEX IF NOT EXISTS idx_documents_system_path_gin
ON documents USING gin (system_path gin_trgm_ops);

-- Enable trigram extension if not already enabled (for pattern matching)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index for root directory queries (first segment of system_path)
-- This supports fast lookups by ROOT directory
CREATE INDEX IF NOT EXISTS idx_documents_root_directory
ON documents ((split_part(system_path, '/', 1)), yacht_id);

-- ============================================================================
-- HELPER FUNCTION: Extract root directory from system_path
-- ============================================================================

CREATE OR REPLACE FUNCTION public.extract_root_directory(system_path text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT split_part(system_path, '/', 1);
$$;

COMMENT ON FUNCTION public.extract_root_directory(text) IS
  'Extracts the ROOT directory from a system_path. '
  'Example: extract_root_directory("03_Engineering/MainEngine") → "03_Engineering"';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'documents'
      AND column_name = 'system_path'
  ) THEN
    RAISE EXCEPTION 'system_path column was not created';
  END IF;

  RAISE NOTICE '✅ system_path column added to documents table';
END $$;

-- Show sample data (if any documents exist)
DO $$
DECLARE
  doc_count int;
BEGIN
  SELECT COUNT(*) INTO doc_count FROM documents;

  IF doc_count > 0 THEN
    RAISE NOTICE 'Sample documents with system_path:';
    RAISE NOTICE '%', (
      SELECT string_agg(
        format('  %s → %s', filename, system_path),
        E'\n'
      )
      FROM (
        SELECT filename, system_path
        FROM documents
        LIMIT 3
      ) sample
    );
  ELSE
    RAISE NOTICE 'No documents yet (table is empty)';
  END IF;
END $$;
