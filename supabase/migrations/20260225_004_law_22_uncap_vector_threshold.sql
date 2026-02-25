-- Migration: 20260225_004_law_22_uncap_vector_threshold.sql
-- Purpose: LAW 22 - Remove pre-fusion threshold amputation from vector search
-- Date: 2026-02-25
--
-- LAW 22: RRF CANDIDATE FREEDOM (NO PRE-FUSION AMPUTATION)
-- Do not use arbitrary scalar thresholds (like vector_score > 0.70) to gate
-- candidates BEFORE Reciprocal Rank Fusion. Use Top-K bounds instead.
-- Let the RRF math naturally push weak matches to the bottom.
--
-- BEFORE: AND (1 - (embedding <=> query)) >= p_match_threshold  <- AMPUTATES
-- AFTER:  ORDER BY ... LIMIT p_match_count                      <- TOP-K ONLY
--
-- This enables semantic queries like "thing that makes drinking water" to find
-- "Watermaker" even when cosine similarity is 0.62 (below the old 0.65 threshold).

-- =============================================================================
-- UPDATE match_search_index RPC - REMOVE THRESHOLD AMPUTATION
-- =============================================================================

CREATE OR REPLACE FUNCTION public.match_search_index(
    p_yacht_id uuid,
    p_query_embedding vector(1536),
    p_match_threshold float DEFAULT 0.0,  -- LAW 22: Ignored, kept for API compatibility
    p_match_count int DEFAULT 60,         -- LAW 22: Increased default for RRF candidate pool
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
    -- LAW 22: NO THRESHOLD AMPUTATION
    -- We use Top-K (LIMIT) to bound candidates, not scalar thresholds.
    -- RRF will naturally push weak matches to the bottom of the fused results.
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
      -- LAW 22: REMOVED threshold check - let RRF handle ranking
      -- OLD: AND (1 - (si.embedding_1536 <=> p_query_embedding)) >= p_match_threshold
    ORDER BY si.embedding_1536 <=> p_query_embedding
    LIMIT p_match_count;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO authenticated;

GRANT EXECUTE ON FUNCTION public.match_search_index(uuid, vector(1536), float, int, text)
    TO service_role;

COMMENT ON FUNCTION public.match_search_index IS
'LAW 21 + LAW 22 Compliant: Vector similarity search on search_index.embedding_1536.

LAW 21: Searches the Storefront (search_index), not the Warehouse (pms_* tables).
LAW 22: Uses Top-K (LIMIT) instead of scalar threshold to bound candidates.
        The p_match_threshold parameter is retained for API compatibility but IGNORED.
        This allows semantic matches like 0.55-0.65 similarity to participate in
        RRF fusion, enabling "thing that makes drinking water" -> "Watermaker".

Parameters:
  - p_yacht_id: Required for tenant isolation (RLS)
  - p_query_embedding: 1536-dimensional query vector
  - p_match_threshold: IGNORED (LAW 22) - retained for API compatibility
  - p_match_count: Top-K limit (default 60 for robust RRF candidate pool)
  - p_object_type: Optional filter (NULL = search all types)

Returns: object_type, object_id, search_text, payload, similarity (1 - cosine_distance)';

-- =============================================================================
-- VERIFICATION
-- =============================================================================
DO $$
DECLARE
    v_function_exists BOOLEAN;
    v_function_def TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'match_search_index'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        -- Verify the function no longer has threshold check
        SELECT pg_get_functiondef(oid) INTO v_function_def
        FROM pg_proc WHERE proname = 'match_search_index';

        IF v_function_def NOT LIKE '%>= p_match_threshold%' THEN
            RAISE NOTICE 'LAW 22 SUCCESS: match_search_index threshold amputation removed';
        ELSE
            RAISE WARNING 'LAW 22 FAILED: match_search_index still has threshold check';
        END IF;
    ELSE
        RAISE WARNING 'match_search_index function does not exist';
    END IF;
END $$;
