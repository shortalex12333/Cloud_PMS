--
-- Email L2.5 Hybrid Linking - match_link_targets RPC
-- Retrieves candidates from search_index with hybrid fusion scoring
--

CREATE OR REPLACE FUNCTION match_link_targets(
    p_yacht_id UUID,
    p_query TEXT,
    p_query_embedding vector(1536) DEFAULT NULL,
    p_object_types TEXT[] DEFAULT NULL,
    p_role TEXT DEFAULT NULL,
    p_days_back INT DEFAULT 365,
    p_limit INT DEFAULT 20
)
RETURNS TABLE(
    object_type TEXT,
    object_id UUID,
    label TEXT,
    payload JSONB,
    s_text DECIMAL,
    s_vector DECIMAL,
    s_recency DECIMAL,
    s_bias DECIMAL,
    rank_text BIGINT,
    rank_vector BIGINT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_recency_lambda DECIMAL := 0.0077;  -- λ for 90-day half-life: ln(2)/90
    v_age_days DECIMAL;
    v_ts_query tsquery;
BEGIN
    -- Build tsquery from p_query for text scoring
    v_ts_query := plainto_tsquery('english', p_query);

    RETURN QUERY
    WITH ranked_text AS (
        SELECT
            si.object_type,
            si.object_id,
            si.search_text AS label,
            si.payload,
            si.updated_at,
            si.embedding,
            -- Text score: ts_rank_cd normalized to [0,1]
            (ts_rank_cd(si.tsv, v_ts_query) / NULLIF(length(si.search_text)::decimal, 0)) AS text_score,
            -- Rank position for RRF
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(si.tsv, v_ts_query) DESC) AS text_rank
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND (p_object_types IS NULL OR si.object_type = ANY(p_object_types))
          AND si.updated_at >= NOW() - (p_days_back || ' days')::interval
          AND si.tsv @@ v_ts_query  -- Must match text query
    ),
    ranked_vector AS (
        SELECT
            si.object_type,
            si.object_id,
            -- Vector score: 1 - cosine distance
            CASE
                WHEN p_query_embedding IS NOT NULL AND si.embedding IS NOT NULL
                THEN (1 - (si.embedding <=> p_query_embedding))::decimal
                ELSE 0::decimal
            END AS vector_score,
            -- Rank position for RRF
            CASE
                WHEN p_query_embedding IS NOT NULL AND si.embedding IS NOT NULL
                THEN ROW_NUMBER() OVER (ORDER BY si.embedding <=> p_query_embedding)
                ELSE NULL
            END AS vector_rank
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND (p_object_types IS NULL OR si.object_type = ANY(p_object_types))
          AND si.updated_at >= NOW() - (p_days_back || ' days')::interval
          AND p_query_embedding IS NOT NULL
          AND si.embedding IS NOT NULL
    ),
    role_bias_lookup AS (
        SELECT
            srb.object_type,
            srb.bias_weight
        FROM search_role_bias srb
        WHERE (p_role IS NULL OR srb.role = p_role)
          AND srb.is_active = TRUE
    )
    SELECT
        rt.object_type,
        rt.object_id,
        COALESCE(rt.label, '')::TEXT AS label,
        COALESCE(rt.payload, '{}'::jsonb) AS payload,
        -- s_text: normalized text score
        COALESCE(rt.text_score, 0)::decimal AS s_text,
        -- s_vector: normalized vector score
        COALESCE(rv.vector_score, 0)::decimal AS s_vector,
        -- s_recency: exponential decay based on age
        (EXP(-v_recency_lambda * EXTRACT(EPOCH FROM (NOW() - rt.updated_at)) / 86400))::decimal AS s_recency,
        -- s_bias: role bias weight (default 0.5 if not found)
        COALESCE(rb.bias_weight, 0.5)::decimal AS s_bias,
        -- rank_text: position in text ranking
        rt.text_rank,
        -- rank_vector: position in vector ranking
        COALESCE(rv.vector_rank, 999999)
    FROM ranked_text rt
    LEFT JOIN ranked_vector rv ON rv.object_type = rt.object_type AND rv.object_id = rt.object_id
    LEFT JOIN role_bias_lookup rb ON rb.object_type = rt.object_type
    ORDER BY
        -- Simple weighted fusion as default ordering
        (0.45 * COALESCE(rt.text_score, 0) +
         0.35 * COALESCE(rv.vector_score, 0) +
         0.15 * (EXP(-v_recency_lambda * EXTRACT(EPOCH FROM (NOW() - rt.updated_at)) / 86400)) +
         0.05 * COALESCE(rb.bias_weight, 0.5)) DESC
    LIMIT p_limit;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION match_link_targets TO authenticated;
GRANT EXECUTE ON FUNCTION match_link_targets TO service_role;

-- Comment
COMMENT ON FUNCTION match_link_targets IS 'L2.5 Hybrid linking: queries search_index with text + vector + recency + role bias fusion';
