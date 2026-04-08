-- =============================================================================
-- Add trigram index on documents.filename for fuzzy file reference matching
-- =============================================================================
-- Used by the import pipeline's file reference resolver to match legacy PMS
-- file references (e.g., DRAWING_REF) against existing yacht documents.
-- pg_trgm is pre-installed on Supabase but may need explicit extension creation.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- doc_metadata is the base table; "documents" is a view over it.
-- Index must target the base table.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_metadata_filename_trgm
ON doc_metadata USING gin (LOWER(filename) gin_trgm_ops);

COMMENT ON INDEX idx_doc_metadata_filename_trgm IS
  'Trigram index for fuzzy filename matching during PMS import file reference resolution';
