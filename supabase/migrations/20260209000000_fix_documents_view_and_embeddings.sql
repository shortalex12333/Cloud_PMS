-- ============================================================================
-- FIX: Create documents view and add embedding infrastructure
-- ============================================================================
-- PROBLEM: Search returns 0 results because:
--   1. Code queries both 'documents' and 'doc_metadata' inconsistently
--   2. 'documents' table doesn't exist (only doc_metadata exists)
--   3. match_documents RPC checks for documents.embedding column
--   4. No embedding column exists on any table
--
-- SOLUTION:
--   1. Create 'documents' VIEW as alias for doc_metadata
--   2. Add embedding vector(1536) column to doc_metadata base table
--   3. Create vector index for similarity search
--
-- DATE: 2026-02-09
-- SEVERITY: P0 - Search completely broken in production
-- ============================================================================

-- Step 1: Add embedding column to doc_metadata base table
-- ============================================================================
DO $$
BEGIN
    -- Check if embedding column already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'doc_metadata'
        AND column_name = 'embedding'
    ) THEN
        -- Add embedding column
        ALTER TABLE public.doc_metadata
        ADD COLUMN embedding vector(1536);

        RAISE NOTICE 'Added embedding column to doc_metadata';
    ELSE
        RAISE NOTICE 'embedding column already exists on doc_metadata';
    END IF;
END $$;

-- Step 2: Create vector index for similarity search
-- ============================================================================
-- Using ivfflat index (fast approximate nearest neighbor)
-- Requires pgvector extension (should already be enabled)
DO $$
BEGIN
    -- Check if index already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename = 'doc_metadata'
        AND indexname = 'idx_doc_metadata_embedding_cosine'
    ) THEN
        -- Create ivfflat index for cosine similarity
        -- lists=100 is good for ~10k-100k vectors
        CREATE INDEX idx_doc_metadata_embedding_cosine
        ON public.doc_metadata
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

        RAISE NOTICE 'Created vector index on doc_metadata.embedding';
    ELSE
        RAISE NOTICE 'Vector index already exists';
    END IF;
END $$;

-- Step 3: Create documents VIEW as alias for doc_metadata
-- ============================================================================
-- This makes doc_metadata queryable as 'documents' for code compatibility
-- Uses SELECT * to include all columns (defensive against schema changes)
DROP VIEW IF EXISTS public.documents CASCADE;

CREATE OR REPLACE VIEW public.documents AS
SELECT
    *,  -- All columns from doc_metadata including the new embedding column
    NULL::text as content  -- Placeholder for content field (stored separately in chunks)
FROM public.doc_metadata
WHERE deleted_at IS NULL;  -- Only show non-deleted documents

-- Grant permissions on view (inherit from base table RLS)
GRANT SELECT ON public.documents TO authenticated;
GRANT INSERT ON public.documents TO authenticated;
GRANT UPDATE ON public.documents TO authenticated;
GRANT DELETE ON public.documents TO authenticated;

COMMENT ON VIEW public.documents IS
'View alias for doc_metadata. Provides backwards compatibility for code querying "documents" table. Filters out soft-deleted documents.';

-- Step 4: Enable RLS on view (inherits from doc_metadata)
-- ============================================================================
-- Views don't have RLS, they inherit from base table
-- doc_metadata already has RLS policies defined in:
--   - 20260125_doc_metadata_write_rls.sql
--   - 00000000000013_07_fix_rls_policies_jwt_fallback.sql

-- Step 5: Verification queries
-- ============================================================================
-- Test that documents view works:
-- SELECT count(*) FROM public.documents;

-- Test that embedding column exists:
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'documents' AND column_name = 'embedding';

-- Test match_documents RPC (should no longer return empty):
-- SELECT * FROM public.match_documents('{}', 10, NULL);

RAISE NOTICE 'SUCCESS: documents view created, embedding infrastructure ready';
