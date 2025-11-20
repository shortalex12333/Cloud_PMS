-- ================================================================
-- CELESTEOS SEARCH ENGINE - SUPABASE SETUP SCRIPT
-- ================================================================
-- Run this in Supabase SQL Editor BEFORE deploying search engine
-- ================================================================

-- ================================================================
-- 1. ENABLE PGVECTOR EXTENSION
-- ================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT * FROM pg_extension WHERE extname = 'vector';


-- ================================================================
-- 2. CREATE DOCUMENT_CHUNKS TABLE (if not exists)
-- ================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  document_id UUID NOT NULL,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  page_number INT,
  embedding VECTOR(1536),  -- CRITICAL: Must be 1536 for text-embedding-3-small
  equipment_ids UUID[],
  fault_codes TEXT[],
  tags TEXT[],
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE document_chunks IS 'Document chunks with vector embeddings for semantic search';
COMMENT ON COLUMN document_chunks.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';


-- ================================================================
-- 3. CREATE INDEXES
-- ================================================================

-- Vector similarity search index (IVFFlat)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Yacht ID filtering index
CREATE INDEX IF NOT EXISTS document_chunks_yacht_id_idx
ON document_chunks(yacht_id);

-- Document ID index
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
ON document_chunks(document_id);

-- Metadata GIN index for JSON filtering
CREATE INDEX IF NOT EXISTS document_chunks_metadata_idx
ON document_chunks USING gin(metadata);


-- ================================================================
-- 4. CREATE MATCH_DOCUMENTS FUNCTION
-- ================================================================

CREATE OR REPLACE FUNCTION public.match_documents(
  filter JSONB,
  match_count INT,
  query_embedding VECTOR(1536)
)
RETURNS TABLE (
  id UUID,
  yacht_id UUID,
  document_id UUID,
  chunk_index INT,
  text TEXT,
  page_number INT,
  embedding VECTOR(1536),
  equipment_ids UUID[],
  fault_codes TEXT[],
  tags TEXT[],
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    v.id,
    v.yacht_id,
    v.document_id,
    v.chunk_index,
    v.text,
    v.page_number,
    v.embedding,
    v.equipment_ids,
    v.fault_codes,
    v.tags,
    v.metadata,
    1 - (v.embedding <=> match_documents.query_embedding) AS similarity
  FROM document_chunks v
  WHERE v.metadata @> filter
  ORDER BY v.embedding <=> match_documents.query_embedding
  LIMIT match_count;
END;
$$;

-- Add comment
COMMENT ON FUNCTION match_documents IS 'Vector similarity search for document chunks with metadata filtering';


-- ================================================================
-- 5. CREATE CELESTE_CHUNKS TABLE (Global Knowledge)
-- ================================================================

CREATE TABLE IF NOT EXISTS celeste_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  embedding VECTOR(1536),
  equipment_tags TEXT[],
  fault_codes TEXT[],
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for global knowledge search
CREATE INDEX IF NOT EXISTS celeste_chunks_embedding_idx
ON celeste_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);


-- ================================================================
-- 6. CREATE MATCH_GLOBAL_DOCUMENTS FUNCTION
-- ================================================================

CREATE OR REPLACE FUNCTION public.match_global_documents(
  filter JSONB,
  match_count INT,
  query_embedding VECTOR(1536)
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  chunk_index INT,
  text TEXT,
  embedding VECTOR(1536),
  equipment_tags TEXT[],
  fault_codes TEXT[],
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    v.id,
    v.document_id,
    v.chunk_index,
    v.text,
    v.embedding,
    v.equipment_tags,
    v.fault_codes,
    v.metadata,
    1 - (v.embedding <=> match_global_documents.query_embedding) AS similarity
  FROM celeste_chunks v
  WHERE v.metadata @> filter
  ORDER BY v.embedding <=> match_global_documents.query_embedding
  LIMIT match_count;
END;
$$;


-- ================================================================
-- 7. ENABLE ROW LEVEL SECURITY (RLS)
-- ================================================================

-- Enable RLS on document_chunks
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can only access their yacht's document chunks" ON document_chunks;
DROP POLICY IF EXISTS "Service role can access all document chunks" ON document_chunks;

-- Policy: Users can only access their yacht's data
CREATE POLICY "Users can only access their yacht's document chunks"
ON document_chunks
FOR SELECT
USING (
  yacht_id IN (
    SELECT yacht_id FROM users
    WHERE auth.uid() = users.id
  )
);

-- Policy: Service role can access all
CREATE POLICY "Service role can access all document chunks"
ON document_chunks
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Authenticated users can insert to their yacht
CREATE POLICY "Users can insert to their yacht's document chunks"
ON document_chunks
FOR INSERT
WITH CHECK (
  yacht_id IN (
    SELECT yacht_id FROM users
    WHERE auth.uid() = users.id
  )
);


-- ================================================================
-- 8. CREATE GRAPH TABLES (if not exist)
-- ================================================================

CREATE TABLE IF NOT EXISTS graph_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  node_type TEXT NOT NULL,  -- 'equipment','part','fault','doc_chunk','work_order'
  ref_table TEXT NOT NULL,  -- source table name
  ref_id UUID NOT NULL,     -- id in source table
  label TEXT NOT NULL,
  properties JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graph_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  from_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  to_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  edge_type TEXT NOT NULL,  -- 'USES_PART','HAS_FAULT','MENTIONS_DOC', etc.
  weight NUMERIC,
  properties JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for graph traversal
CREATE INDEX IF NOT EXISTS graph_nodes_yacht_id_idx ON graph_nodes(yacht_id);
CREATE INDEX IF NOT EXISTS graph_nodes_type_idx ON graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS graph_edges_from_idx ON graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS graph_edges_to_idx ON graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS graph_edges_yacht_id_idx ON graph_edges(yacht_id);


-- ================================================================
-- 9. VERIFICATION QUERIES
-- ================================================================

-- Verify pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Verify document_chunks table structure
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'document_chunks'
ORDER BY ordinal_position;

-- Verify match_documents function exists
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_name = 'match_documents';

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'document_chunks';


-- ================================================================
-- 10. TEST QUERIES
-- ================================================================

-- Test: Create a dummy embedding vector (for testing only)
DO $$
DECLARE
  test_embedding VECTOR(1536);
  test_yacht_id UUID;
BEGIN
  -- Generate random test embedding
  test_embedding := (
    SELECT ARRAY(
      SELECT random()
      FROM generate_series(1, 1536)
    )::VECTOR(1536)
  );

  -- Get or create test yacht
  INSERT INTO yachts (id, name, signature, status)
  VALUES (
    gen_random_uuid(),
    'Test Yacht',
    'test-signature-' || gen_random_uuid(),
    'active'
  )
  ON CONFLICT DO NOTHING
  RETURNING id INTO test_yacht_id;

  -- Note: Actual testing requires real data
  RAISE NOTICE 'Test embedding generated successfully';
  RAISE NOTICE 'Embedding dimension: %', array_length(test_embedding::real[], 1);
END $$;


-- ================================================================
-- DEPLOYMENT COMPLETE
-- ================================================================

-- Summary
SELECT
  'Setup Complete!' as status,
  (SELECT count(*) FROM document_chunks) as total_chunks,
  (SELECT count(DISTINCT yacht_id) FROM document_chunks) as total_yachts,
  (SELECT extversion FROM pg_extension WHERE extname = 'vector') as pgvector_version;
