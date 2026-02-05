-- ============================================================================
-- Migration: 022_hyper_search_vec1536_and_hard_tiers.sql
-- Description: Update RPCs to use embedding_1536 and Hard Tiers ordering
-- Date: 2026-02-05
-- ============================================================================

-- ============================================================================
-- Helper function: Normalize identifier for exact matching
-- ============================================================================

CREATE OR REPLACE FUNCTION public.normalize_ident(val TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT NULLIF(UPPER(REGEXP_REPLACE(COALESCE(val, ''), '[\s\-_]+', '', 'g')), '')
$$;

COMMENT ON FUNCTION public.normalize_ident IS 'Normalize identifier: strip whitespace/dashes, uppercase';

-- ============================================================================
-- hyper_search_multi: Main search RPC with Hard Tiers
-- ============================================================================

CREATE OR REPLACE FUNCTION public.hyper_search_multi(
    p_query TEXT,
    p_org_id UUID,
    p_yacht_id UUID DEFAULT NULL,
    p_types TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 50,
    p_embedding vector(1536) DEFAULT NULL,
    -- Hard Tiers parameters
    p_explicit_types TEXT[] DEFAULT NULL,    -- Domain types from parsed tokens (e.g., 'wo:', 'part:')
    p_filter_only BOOLEAN DEFAULT FALSE,     -- TRUE if "Only" suffix (hard filter)
    p_id_query TEXT DEFAULT NULL             -- Normalized query for ident_norm matching
)
RETURNS TABLE (
    object_type TEXT,
    object_id TEXT,
    search_text TEXT,
    payload JSONB,
    filters JSONB,
    trigram_score REAL,
    vector_score REAL,
    fused_score REAL,
    -- Hard Tiers fields
    exact_id_match BOOLEAN,
    explicit_domain_match BOOLEAN,
    recency_ts TIMESTAMPTZ,
    ident_norm TEXT,
    tier INT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_normalized_id TEXT;
BEGIN
    -- Statement timeout for guardrail
    SET LOCAL statement_timeout = '250ms';

    -- Normalize the ID query
    v_normalized_id := normalize_ident(p_id_query);

    RETURN QUERY
    WITH base_search AS (
        SELECT
            si.object_type,
            si.object_id,
            si.search_text,
            si.payload,
            si.filters,
            si.recency_ts,
            si.ident_norm,
            -- Trigram similarity
            COALESCE(similarity(si.search_text, p_query), 0)::REAL AS trgm_score,
            -- Vector similarity (1536-dim)
            CASE
                WHEN p_embedding IS NOT NULL AND si.embedding_1536 IS NOT NULL
                THEN (1 - (si.embedding_1536 <=> p_embedding))::REAL
                ELSE 0::REAL
            END AS vec_score,
            -- Exact ID match
            CASE
                WHEN v_normalized_id IS NOT NULL
                     AND si.ident_norm IS NOT NULL
                     AND si.ident_norm = v_normalized_id
                THEN TRUE
                ELSE FALSE
            END AS is_exact_id,
            -- Explicit domain match
            CASE
                WHEN p_explicit_types IS NOT NULL
                     AND si.object_type = ANY(p_explicit_types)
                THEN TRUE
                ELSE FALSE
            END AS is_explicit_domain
        FROM search_index si
        WHERE si.org_id = p_org_id
          AND (p_yacht_id IS NULL OR si.yacht_id = p_yacht_id)
          AND (p_types IS NULL OR si.object_type = ANY(p_types))
          -- Hard filter for "Only" mode
          AND (
              NOT p_filter_only
              OR p_explicit_types IS NULL
              OR si.object_type = ANY(p_explicit_types)
          )
          -- At least some match signal
          AND (
              si.search_text % p_query                              -- Trigram
              OR (p_embedding IS NOT NULL
                  AND si.embedding_1536 IS NOT NULL
                  AND si.embedding_1536 <=> p_embedding < 0.5)      -- Vector (cosine < 0.5 = similarity > 0.5)
              OR (v_normalized_id IS NOT NULL
                  AND si.ident_norm = v_normalized_id)              -- Exact ID
          )
    ),
    scored AS (
        SELECT
            b.*,
            -- Fused score: max of trigram and vector
            GREATEST(b.trgm_score, b.vec_score) AS fused,
            -- Compute tier for UI
            CASE
                WHEN b.is_exact_id THEN 1
                WHEN b.is_explicit_domain THEN 2
                WHEN b.recency_ts IS NOT NULL
                     AND b.recency_ts > NOW() - INTERVAL '30 days' THEN 3
                ELSE 4
            END AS computed_tier
        FROM base_search b
        -- Quality gates: minimum relevance OR exact match
        WHERE b.trgm_score >= 0.30
           OR b.vec_score >= 0.75
           OR b.is_exact_id
    )
    SELECT
        s.object_type,
        s.object_id,
        s.search_text,
        s.payload,
        s.filters,
        s.trgm_score AS trigram_score,
        s.vec_score AS vector_score,
        s.fused AS fused_score,
        s.is_exact_id AS exact_id_match,
        s.is_explicit_domain AS explicit_domain_match,
        s.recency_ts,
        s.ident_norm,
        s.computed_tier AS tier
    FROM scored s
    -- Hard Tiers ORDER BY
    ORDER BY
        CASE WHEN s.is_exact_id THEN 0 ELSE 1 END ASC,
        CASE WHEN s.is_explicit_domain THEN 0 ELSE 1 END ASC,
        s.recency_ts DESC NULLS LAST,
        s.fused DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION public.hyper_search_multi IS
'Main search RPC with Hard Tiers ranking. Uses embedding_1536 for vector search.
ORDER BY: exact_id_match, explicit_domain_match, recency_ts, fused_score';

-- ============================================================================
-- hyper_search_docs_by_chunks: Document chunk search with Hard Tiers
-- ============================================================================

CREATE OR REPLACE FUNCTION public.hyper_search_docs_by_chunks(
    p_query TEXT,
    p_org_id UUID,
    p_yacht_id UUID DEFAULT NULL,
    p_doc_types TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 20,
    p_embedding vector(1536) DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    filename TEXT,
    doc_type TEXT,
    storage_path TEXT,
    chunk_id UUID,
    chunk_index INT,
    chunk_content TEXT,
    trigram_score REAL,
    vector_score REAL,
    fused_score REAL,
    recency_ts TIMESTAMPTZ,
    tier INT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    -- Statement timeout
    SET LOCAL statement_timeout = '300ms';

    RETURN QUERY
    WITH chunk_search AS (
        SELECT
            c.document_id,
            c.id AS chunk_id,
            c.chunk_index,
            c.content,
            -- Trigram similarity on chunk content
            COALESCE(similarity(c.content, p_query), 0)::REAL AS trgm_score,
            -- Vector similarity (1536-dim)
            CASE
                WHEN p_embedding IS NOT NULL AND c.embedding_1536 IS NOT NULL
                THEN (1 - (c.embedding_1536 <=> p_embedding))::REAL
                ELSE 0::REAL
            END AS vec_score
        FROM search_document_chunks c
        JOIN doc_metadata d ON d.id = c.document_id
        WHERE d.org_id = p_org_id
          AND (p_yacht_id IS NULL OR d.yacht_id = p_yacht_id)
          AND (p_doc_types IS NULL OR d.doc_type = ANY(p_doc_types))
          AND (
              c.content % p_query
              OR (p_embedding IS NOT NULL
                  AND c.embedding_1536 IS NOT NULL
                  AND c.embedding_1536 <=> p_embedding < 0.5)
          )
    ),
    ranked_chunks AS (
        SELECT
            cs.*,
            GREATEST(cs.trgm_score, cs.vec_score) AS fused,
            ROW_NUMBER() OVER (
                PARTITION BY cs.document_id
                ORDER BY GREATEST(cs.trgm_score, cs.vec_score) DESC
            ) AS chunk_rank
        FROM chunk_search cs
        WHERE cs.trgm_score >= 0.25 OR cs.vec_score >= 0.70
    ),
    best_chunks AS (
        SELECT * FROM ranked_chunks WHERE chunk_rank = 1
    )
    SELECT
        d.id AS document_id,
        d.filename,
        d.doc_type,
        d.storage_path,
        bc.chunk_id,
        bc.chunk_index,
        bc.content AS chunk_content,
        bc.trgm_score AS trigram_score,
        bc.vec_score AS vector_score,
        bc.fused AS fused_score,
        d.updated_at AS recency_ts,
        CASE
            WHEN d.updated_at > NOW() - INTERVAL '30 days' THEN 3
            ELSE 4
        END AS tier
    FROM best_chunks bc
    JOIN doc_metadata d ON d.id = bc.document_id
    ORDER BY
        d.updated_at DESC NULLS LAST,
        bc.fused DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION public.hyper_search_docs_by_chunks IS
'Document chunk search with 1536-dim vectors. Returns best matching chunk per document.';

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT EXECUTE ON FUNCTION public.hyper_search_multi TO authenticated;
GRANT EXECUTE ON FUNCTION public.hyper_search_docs_by_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION public.normalize_ident TO authenticated;
