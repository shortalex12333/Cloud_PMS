-- Migration: Create match_search_index RPC
-- Description: LAW 21 - Vector search against search_index with embedding_1536 column
-- Supports the orchestration executor for semantic search queries

-- =============================================================================
-- FUNCTION: match_search_index
-- =============================================================================
-- Performs cosine similarity search on the search_index table using embedding_1536
-- Returns object_type, object_id, search_text, payload, and similarity score
-- Filters by yacht_id for tenant isolation (required)
-- Optionally filters by object_type for scoped searches

CREATE OR REPLACE FUNCTION public.match_search_index(
    p_yacht_id uuid,
    p_query_embedding vector(1536),
    p_match_threshold float DEFAULT 0.70,
    p_match_count int DEFAULT 20,
    p_object_type text DEFAULT NULL
)
RETURNS TABLE(
    object_type text,
    object_id uuid,
    search_text text,
    payload jsonb,
    similarity float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        si.object_type,
        si.object_id,
        si.search_text,
        si.payload,
        (1 - (si.embedding_1536 <=> p_query_embedding))::float AS similarity
    FROM public.search_index si
    WHERE si.yacht_id = p_yacht_id
      AND si.embedding_1536 IS NOT NULL
      AND (p_object_type IS NULL OR si.object_type = p_object_type)
      AND (1 - (si.embedding_1536 <=> p_query_embedding)) >= p_match_threshold
    ORDER BY si.embedding_1536 <=> p_query_embedding
    LIMIT p_match_count;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO authenticated;

-- Grant execute to service role for backend operations
GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO service_role;

-- Add documentation
COMMENT ON FUNCTION public.match_search_index IS
'LAW 21: Vector similarity search on search_index table using embedding_1536 column.
Uses cosine similarity: 1 - (embedding_1536 <=> query_embedding).
Requires yacht_id for tenant isolation. Optional object_type filter.
Returns object_type, object_id, search_text, payload, and similarity score.';
