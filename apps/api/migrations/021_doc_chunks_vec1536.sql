-- ============================================================================
-- Migration: 021_doc_chunks_vec1536.sql
-- Description: Add 1536-dim embedding support to search_document_chunks
-- Date: 2026-02-05
-- ============================================================================

-- 1536-dim embedding column for document chunks
ALTER TABLE public.search_document_chunks ADD COLUMN IF NOT EXISTS embedding_1536 vector(1536);
ALTER TABLE public.search_document_chunks ADD COLUMN IF NOT EXISTS embedding_model TEXT;
ALTER TABLE public.search_document_chunks ADD COLUMN IF NOT EXISTS embedding_version INT;
ALTER TABLE public.search_document_chunks ADD COLUMN IF NOT EXISTS embedding_hash TEXT;

COMMENT ON COLUMN public.search_document_chunks.embedding_1536 IS 'OpenAI text-embedding-3-small 1536-dim vector';
COMMENT ON COLUMN public.search_document_chunks.embedding_model IS 'Model used to generate embedding';
COMMENT ON COLUMN public.search_document_chunks.embedding_version IS 'Schema version for embedding (current: 3)';
COMMENT ON COLUMN public.search_document_chunks.embedding_hash IS 'SHA-256 hash of content for delta embedding';

-- ============================================================================
-- HNSW Index for 1536-dim vectors on chunks
-- ============================================================================

-- HNSW index for cosine similarity on chunk embeddings
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sdc_vec1536_hnsw
    ON public.search_document_chunks
    USING hnsw (embedding_1536 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index for finding chunks needing embedding
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sdc_needs_embedding
    ON public.search_document_chunks (created_at DESC)
    WHERE embedding_1536 IS NULL
       OR embedding_hash IS NULL
       OR embedding_version IS NULL
       OR embedding_version < 3;

-- ============================================================================
-- NOTE: Do NOT drop legacy embedding column yet
-- ============================================================================
