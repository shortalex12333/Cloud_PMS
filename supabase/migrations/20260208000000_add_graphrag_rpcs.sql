-- GraphRAG Support Functions
-- Created: 2026-02-08
-- Purpose: Add missing RPCs for GraphRAG query execution
-- Safe stubs that handle missing vector infrastructure gracefully

-- ============================================================================
-- match_documents: Vector similarity search with fallback
-- ============================================================================
CREATE OR REPLACE FUNCTION public.match_documents(
    filter jsonb DEFAULT '{}'::jsonb,
    match_count int DEFAULT 10,
    query_embedding vector(1536) DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Safe stub: returns empty result set if vector infrastructure not ready
    -- In production with embeddings, this would perform similarity search

    -- Check if query_embedding is provided and vector column exists
    IF query_embedding IS NOT NULL AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'documents'
        AND column_name = 'embedding'
    ) THEN
        -- Perform vector similarity search when infrastructure exists
        RETURN QUERY
        SELECT
            d.id,
            d.content,
            d.metadata,
            1 - (d.embedding <=> query_embedding) as similarity
        FROM documents d
        WHERE (filter = '{}'::jsonb OR d.metadata @> filter)
        ORDER BY d.embedding <=> query_embedding
        LIMIT match_count;
    ELSE
        -- Safe fallback: return empty set
        -- This allows GraphRAG to continue without crashing
        RETURN;
    END IF;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.match_documents TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents TO service_role;

COMMENT ON FUNCTION public.match_documents IS
'Vector similarity search for documents. Returns empty set if embedding infrastructure not available. Safe for GraphRAG degraded mode.';

-- ============================================================================
-- resolve_entity_alias: Entity canonicalization with fallback
-- ============================================================================
CREATE OR REPLACE FUNCTION public.resolve_entity_alias(
    p_yacht_id uuid,
    p_entity_type text,
    p_alias_text text
)
RETURNS TABLE (
    canonical_id uuid,
    canonical_name text,
    entity_type text,
    confidence float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Safe stub: attempts lookup from graph_nodes if exists, else NULL
    -- In production, this would perform fuzzy matching and scoring

    -- Check if graph_nodes table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'graph_nodes'
    ) THEN
        -- Attempt exact match first
        RETURN QUERY
        SELECT
            gn.id as canonical_id,
            gn.name as canonical_name,
            gn.node_type as entity_type,
            1.0 as confidence
        FROM graph_nodes gn
        WHERE gn.yacht_id = p_yacht_id
        AND gn.node_type = p_entity_type
        AND LOWER(gn.name) = LOWER(p_alias_text)
        LIMIT 1;

        -- If no exact match, try fuzzy match (if pg_trgm available)
        IF NOT FOUND THEN
            RETURN QUERY
            SELECT
                gn.id as canonical_id,
                gn.name as canonical_name,
                gn.node_type as entity_type,
                0.7 as confidence  -- Lower confidence for fuzzy match
            FROM graph_nodes gn
            WHERE gn.yacht_id = p_yacht_id
            AND gn.node_type = p_entity_type
            AND gn.name ILIKE '%' || p_alias_text || '%'
            LIMIT 1;
        END IF;
    ELSE
        -- Safe fallback: return empty (GraphRAG continues without entity resolution)
        RETURN;
    END IF;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.resolve_entity_alias TO authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_entity_alias TO service_role;

COMMENT ON FUNCTION public.resolve_entity_alias IS
'Resolves entity aliases to canonical IDs. Best-effort with fallback to empty result if graph infrastructure unavailable.';

-- ============================================================================
-- resolve_symptom_alias: Symptom canonicalization stub
-- ============================================================================
CREATE OR REPLACE FUNCTION public.resolve_symptom_alias(
    p_alias_text text
)
RETURNS TABLE (
    symptom_id uuid,
    symptom_name text,
    category text
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Safe stub: attempts lookup from symptoms table if exists, else NULL
    -- This is a simple pass-through for now

    -- Check if symptoms table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'symptoms'
    ) THEN
        RETURN QUERY
        SELECT
            s.id as symptom_id,
            s.name as symptom_name,
            s.category
        FROM symptoms s
        WHERE LOWER(s.name) = LOWER(p_alias_text)
        OR s.name ILIKE '%' || p_alias_text || '%'
        LIMIT 1;
    ELSE
        -- Safe fallback: return empty
        RETURN;
    END IF;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.resolve_symptom_alias TO authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_symptom_alias TO service_role;

COMMENT ON FUNCTION public.resolve_symptom_alias IS
'Resolves symptom aliases to canonical symptom records. Returns empty if symptoms table unavailable.';

-- ============================================================================
-- Verification queries (for testing)
-- ============================================================================

-- Test match_documents (should return empty, not error)
-- SELECT * FROM public.match_documents('{}', 10, NULL);

-- Test resolve_entity_alias (should return empty, not error)
-- SELECT * FROM public.resolve_entity_alias(
--     '85fe1119-b04c-41ac-80f1-829d23322598'::uuid,
--     'equipment',
--     'generator'
-- );

-- Test resolve_symptom_alias (should return empty, not error)
-- SELECT * FROM public.resolve_symptom_alias('overheating');
