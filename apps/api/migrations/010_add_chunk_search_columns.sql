-- Migration 010: Add Search Columns to search_document_chunks
-- Purpose: Enable FTS + trigram search on chunks, add offset columns for citations
--
-- Current schema has: document_id, chunk_index, content, embedding, metadata
-- Missing for RAG: search_text (trigram), tsv (FTS), org_id (RLS), offsets (citations)

-- ============================================================================
-- Step 1: Add missing columns
-- ============================================================================

-- Add search_text column (mirrors content for trigram indexing)
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS search_text TEXT;

-- Add org_id for RLS (will copy from yacht_id since they're 1:1 in this tenant)
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS org_id UUID;

-- Add offset columns for PDF citation highlighting
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS start_offset INT DEFAULT 0;

ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS end_offset INT DEFAULT 0;

ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS global_offset_start INT DEFAULT 0;

-- Add tsvector for FTS (generated from content)
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS tsv TSVECTOR
GENERATED ALWAYS AS (to_tsvector('english', COALESCE(content, ''))) STORED;

-- ============================================================================
-- Step 2: Backfill search_text and org_id
-- ============================================================================

-- Copy content to search_text where NULL
UPDATE search_document_chunks
SET search_text = content
WHERE search_text IS NULL AND content IS NOT NULL;

-- Copy yacht_id to org_id (they're the same in this single-tenant setup)
-- In multi-tenant, you'd join to a yacht→org mapping table
UPDATE search_document_chunks
SET org_id = yacht_id
WHERE org_id IS NULL AND yacht_id IS NOT NULL;

-- Set end_offset based on content length where not set
UPDATE search_document_chunks
SET end_offset = LENGTH(content)
WHERE end_offset = 0 AND content IS NOT NULL;

-- ============================================================================
-- Step 3: Create indexes
-- ============================================================================

-- GIN index for FTS on tsv
CREATE INDEX IF NOT EXISTS ix_sdc_tsv
ON search_document_chunks USING gin (tsv);

-- GIN index for trigram on search_text
CREATE INDEX IF NOT EXISTS ix_sdc_trgm
ON search_document_chunks USING gin (search_text gin_trgm_ops);

-- HNSW index for vector search
CREATE INDEX IF NOT EXISTS ix_sdc_vector
ON search_document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- RLS helper indexes
CREATE INDEX IF NOT EXISTS ix_sdc_org_doc
ON search_document_chunks (org_id, document_id);

CREATE INDEX IF NOT EXISTS ix_sdc_yacht
ON search_document_chunks (yacht_id);

CREATE INDEX IF NOT EXISTS ix_sdc_doc_id
ON search_document_chunks (document_id);

-- ============================================================================
-- Step 4: Enable RLS
-- ============================================================================

ALTER TABLE search_document_chunks ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if any
DROP POLICY IF EXISTS sdc_yacht_isolation ON search_document_chunks;
DROP POLICY IF EXISTS chunks_select ON search_document_chunks;

-- Create RLS policy based on yacht_id (since org_id = yacht_id in this setup)
-- Uses JWT claims from request context
CREATE POLICY sdc_select_policy ON search_document_chunks
FOR SELECT USING (
    yacht_id = NULLIF(
        current_setting('request.jwt.claims', true)::jsonb ->> 'yacht_id',
        ''
    )::uuid
);

-- ============================================================================
-- Step 5: Analyze for query planner
-- ============================================================================

ANALYZE search_document_chunks;

-- ============================================================================
-- Verification queries (run manually after migration)
-- ============================================================================
-- SELECT COUNT(*) FROM search_document_chunks WHERE search_text IS NOT NULL;
-- SELECT COUNT(*) FROM search_document_chunks WHERE org_id IS NOT NULL;
-- SELECT COUNT(*) FROM search_document_chunks WHERE tsv IS NOT NULL;
-- EXPLAIN ANALYZE SELECT * FROM search_document_chunks WHERE search_text % 'test query' LIMIT 10;

COMMENT ON COLUMN search_document_chunks.search_text IS 'Copy of content for trigram search (% operator)';
COMMENT ON COLUMN search_document_chunks.tsv IS 'Generated tsvector for FTS search';
COMMENT ON COLUMN search_document_chunks.org_id IS 'Organization ID for RLS (copied from yacht_id)';
COMMENT ON COLUMN search_document_chunks.global_offset_start IS 'Character offset in full document for PDF highlighting';
