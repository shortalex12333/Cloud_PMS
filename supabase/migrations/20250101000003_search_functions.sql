-- ============================================================================
-- Migration: Search Functions for Document RAG
-- Version: 20250101000003
-- Description: Create semantic search functions using pgvector
-- ============================================================================

-- ============================================================================
-- FUNCTION: match_documents
-- Purpose: Semantic search over document_chunks using vector similarity
-- Used by: n8n Vector Store Node, API search endpoints
-- ============================================================================

CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  metadata JSONB,
  page_number INTEGER,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  -- Get current user's yacht_id for RLS enforcement
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  -- If no user found, return empty result (authentication required)
  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  -- Return matching document chunks with similarity score
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.text AS content,
    dc.metadata,
    dc.page_number,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  WHERE
    dc.yacht_id = user_yacht_id
    AND dc.metadata @> filter  -- JSONB containment for filtering
    AND dc.embedding IS NOT NULL  -- Only chunks with embeddings
  ORDER BY dc.embedding <=> query_embedding  -- Cosine distance
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.match_documents IS 'Semantic search over document chunks using vector similarity (n8n compatible)';

-- ============================================================================
-- FUNCTION: search_documents_advanced
-- Purpose: Advanced search with equipment/work order context
-- Returns enriched results with document metadata
-- ============================================================================

CREATE OR REPLACE FUNCTION public.search_documents_advanced(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  equipment_filter UUID DEFAULT NULL,
  category_filter TEXT DEFAULT NULL,
  min_similarity FLOAT DEFAULT 0.5
)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  document_filename TEXT,
  document_category TEXT,
  chunk_text TEXT,
  page_number INTEGER,
  similarity FLOAT,
  metadata JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  -- Get current user's yacht_id
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    dc.id AS chunk_id,
    dc.document_id,
    d.filename AS document_filename,
    d.category AS document_category,
    dc.text AS chunk_text,
    dc.page_number,
    (1 - (dc.embedding <=> query_embedding)) AS similarity,
    dc.metadata
  FROM document_chunks dc
  INNER JOIN documents d ON dc.document_id = d.id
  WHERE
    dc.yacht_id = user_yacht_id
    AND dc.embedding IS NOT NULL
    AND (1 - (dc.embedding <=> query_embedding)) >= min_similarity
    AND (equipment_filter IS NULL OR d.metadata @> jsonb_build_object('equipment_id', equipment_filter::text))
    AND (category_filter IS NULL OR d.category = category_filter)
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.search_documents_advanced IS 'Advanced semantic search with document metadata and filtering';

-- ============================================================================
-- FUNCTION: hybrid_search
-- Purpose: Combine vector similarity with full-text search
-- Uses both semantic meaning and keyword matching
-- ============================================================================

CREATE OR REPLACE FUNCTION public.hybrid_search(
  query_text TEXT,
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  vector_weight FLOAT DEFAULT 0.7,
  text_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  document_filename TEXT,
  chunk_text TEXT,
  page_number INTEGER,
  vector_similarity FLOAT,
  text_rank FLOAT,
  combined_score FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
BEGIN
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    dc.id AS chunk_id,
    dc.document_id,
    d.filename AS document_filename,
    dc.text AS chunk_text,
    dc.page_number,
    (1 - (dc.embedding <=> query_embedding)) AS vector_similarity,
    ts_rank(to_tsvector('english', dc.text), plainto_tsquery('english', query_text)) AS text_rank,
    (
      (1 - (dc.embedding <=> query_embedding)) * vector_weight +
      ts_rank(to_tsvector('english', dc.text), plainto_tsquery('english', query_text)) * text_weight
    ) AS combined_score
  FROM document_chunks dc
  INNER JOIN documents d ON dc.document_id = d.id
  WHERE
    dc.yacht_id = user_yacht_id
    AND dc.embedding IS NOT NULL
    AND (
      dc.embedding <=> query_embedding < 0.5  -- Vector similarity threshold
      OR
      to_tsvector('english', dc.text) @@ plainto_tsquery('english', query_text)  -- Text match
    )
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.hybrid_search IS 'Hybrid search combining vector similarity and full-text search';

-- ============================================================================
-- FUNCTION: get_similar_chunks
-- Purpose: Find similar chunks to a given document chunk
-- Useful for "related documents" feature
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_similar_chunks(
  source_chunk_id UUID,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  document_filename TEXT,
  chunk_text TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  user_yacht_id UUID;
  source_embedding VECTOR(1536);
BEGIN
  -- Get user's yacht_id
  SELECT yacht_id INTO user_yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF user_yacht_id IS NULL THEN
    RETURN;
  END IF;

  -- Get embedding of source chunk
  SELECT embedding INTO source_embedding
  FROM document_chunks
  WHERE id = source_chunk_id AND yacht_id = user_yacht_id;

  IF source_embedding IS NULL THEN
    RETURN;
  END IF;

  -- Find similar chunks (excluding the source chunk)
  RETURN QUERY
  SELECT
    dc.id AS chunk_id,
    dc.document_id,
    d.filename AS document_filename,
    dc.text AS chunk_text,
    (1 - (dc.embedding <=> source_embedding)) AS similarity
  FROM document_chunks dc
  INNER JOIN documents d ON dc.document_id = d.id
  WHERE
    dc.yacht_id = user_yacht_id
    AND dc.id != source_chunk_id
    AND dc.embedding IS NOT NULL
  ORDER BY dc.embedding <=> source_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.get_similar_chunks IS 'Find similar document chunks for "related documents" feature';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION public.match_documents TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_documents_advanced TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_similar_chunks TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to test)
-- ============================================================================

-- Test match_documents (replace with actual embedding):
-- SELECT * FROM match_documents(
--   '[0.1, 0.2, ...]'::vector(1536),
--   10,
--   '{}'::jsonb
-- );

-- Test search_documents_advanced:
-- SELECT * FROM search_documents_advanced(
--   '[0.1, 0.2, ...]'::vector(1536),
--   10,
--   NULL,
--   'manual',
--   0.5
-- );
