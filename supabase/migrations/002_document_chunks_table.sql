-- CelesteOS Document Chunks Table Migration
-- Version: 002
-- Description: Creates document_chunks table for RAG with pgvector embeddings

-- ============================================================
-- 1. Enable pgvector Extension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. Document Chunks Table
-- ============================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    embedding vector(1536), -- OpenAI text-embedding-3-small produces 1536-dim vectors
    equipment_ids UUID[],
    fault_codes TEXT[],
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. Indexes for Performance
-- ============================================================

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_chunks_yacht_id ON document_chunks(yacht_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks(chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_created_at ON document_chunks(created_at DESC);

-- Vector similarity search index (IVFFlat for cosine similarity)
-- Note: This index improves search performance but requires tuning for large datasets
-- lists parameter should be sqrt(total_rows) - adjust after inserting data
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- GIN indexes for array columns (equipment_ids, fault_codes, tags)
CREATE INDEX IF NOT EXISTS idx_chunks_equipment_ids ON document_chunks USING GIN(equipment_ids);
CREATE INDEX IF NOT EXISTS idx_chunks_fault_codes ON document_chunks USING GIN(fault_codes);
CREATE INDEX IF NOT EXISTS idx_chunks_tags ON document_chunks USING GIN(tags);

-- ============================================================
-- 4. Row Level Security (RLS)
-- ============================================================

ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access chunks from their yacht
CREATE POLICY chunks_yacht_isolation ON document_chunks
    FOR ALL
    USING (yacht_id::text = current_setting('app.current_yacht_id', true));

-- ============================================================
-- 5. Helper Functions
-- ============================================================

-- Function to search for similar chunks using cosine similarity
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1536),
    query_yacht_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    chunk_index INT,
    text TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id AS chunk_id,
        dc.document_id,
        dc.chunk_index,
        dc.text,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        dc.metadata
    FROM document_chunks dc
    WHERE
        dc.yacht_id = query_yacht_id
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get chunk count for a document
CREATE OR REPLACE FUNCTION get_document_chunk_count(doc_id UUID)
RETURNS INTEGER
LANGUAGE sql
AS $$
    SELECT COUNT(*)::INTEGER
    FROM document_chunks
    WHERE document_id = doc_id;
$$;

-- ============================================================
-- 6. Triggers
-- ============================================================

-- Trigger to update document.indexed flag when all chunks are inserted
CREATE OR REPLACE FUNCTION update_document_indexed_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if this is the last chunk
    -- (This is a simple implementation - enhance for production)
    UPDATE documents
    SET
        status = 'indexed',
        indexed = TRUE,
        indexed_at = NOW(),
        updated_at = NOW()
    WHERE
        id = NEW.document_id
        AND status = 'indexing';

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: This trigger is commented out as the n8n workflow handles status updates
-- Uncomment if you want automatic status updates on chunk insert
-- CREATE TRIGGER trigger_update_document_indexed
--     AFTER INSERT ON document_chunks
--     FOR EACH ROW
--     EXECUTE FUNCTION update_document_indexed_status();

-- ============================================================
-- 7. Comments for Documentation
-- ============================================================

COMMENT ON TABLE document_chunks IS 'Text chunks with embeddings for RAG (Retrieval-Augmented Generation)';
COMMENT ON COLUMN document_chunks.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';
COMMENT ON COLUMN document_chunks.chunk_index IS 'Sequential index of chunk within document';
COMMENT ON COLUMN document_chunks.text IS 'Raw text content of this chunk';
COMMENT ON COLUMN document_chunks.page_number IS 'Source page number (if available from OCR)';
COMMENT ON COLUMN document_chunks.equipment_ids IS 'Array of equipment UUIDs mentioned in this chunk';
COMMENT ON COLUMN document_chunks.fault_codes IS 'Array of fault codes found in this chunk';
COMMENT ON COLUMN document_chunks.metadata IS 'Additional metadata (word_count, embedding_model, etc.)';

COMMENT ON FUNCTION search_similar_chunks IS 'Search for chunks similar to a query embedding using cosine similarity';
COMMENT ON FUNCTION get_document_chunk_count IS 'Get total number of chunks for a document';

-- ============================================================
-- 8. Grants (if using service role)
-- ============================================================

-- Grant permissions to service role (adjust based on your Supabase setup)
-- These are typically handled by Supabase automatically, but included for reference

-- GRANT ALL ON document_chunks TO service_role;
-- GRANT ALL ON FUNCTION search_similar_chunks TO service_role;
-- GRANT ALL ON FUNCTION get_document_chunk_count TO service_role;

-- ============================================================
-- 9. Validation Queries
-- ============================================================

-- Uncomment to verify setup:

-- Check if pgvector extension is enabled
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check table structure
-- \d document_chunks

-- Check indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks';

-- Test similarity search (after inserting data)
-- SELECT * FROM search_similar_chunks(
--     (SELECT embedding FROM document_chunks LIMIT 1),
--     (SELECT yacht_id FROM yachts LIMIT 1),
--     0.7,
--     5
-- );
