-- ============================================================================
-- Migration 030: Deterministic Fusion Scoring Model
-- ============================================================================

-- 1. Create role bias table
CREATE TABLE IF NOT EXISTS public.search_role_bias (
    role TEXT NOT NULL,
    lens TEXT NOT NULL,
    doc_type TEXT,
    part_type TEXT,
    bias NUMERIC DEFAULT 0.0,
    UNIQUE (role, lens, doc_type, part_type)
);

COMMENT ON TABLE public.search_role_bias IS
    'Role-based scoring biases for search results. Used to boost relevance based on user role and content type.';

-- 2. Seed default role biases
INSERT INTO public.search_role_bias (role, lens, doc_type, part_type, bias) VALUES
    -- Captain biases
    ('captain', 'document', 'certificate', NULL, 0.15),
    ('captain', 'document', 'compliance', NULL, 0.15),
    ('captain', 'document', 'report', NULL, 0.10),
    ('captain', 'work_order', NULL, NULL, 0.05),
    ('captain', 'crew', NULL, NULL, 0.10),

    -- HOD (Chief Engineer) biases
    ('hod', 'equipment', NULL, NULL, 0.15),
    ('hod', 'work_order', NULL, NULL, 0.15),
    ('hod', 'part', NULL, NULL, 0.10),
    ('hod', 'fault', NULL, NULL, 0.10),
    ('hod', 'document', 'manual', NULL, 0.10),

    -- Engineer biases
    ('engineer', 'equipment', NULL, NULL, 0.20),
    ('engineer', 'part', NULL, NULL, 0.20),
    ('engineer', 'fault', NULL, NULL, 0.15),
    ('engineer', 'work_order', NULL, NULL, 0.10),
    ('engineer', 'document', 'manual', NULL, 0.15),
    ('engineer', 'document', 'schematic', NULL, 0.15),

    -- Crew biases
    ('crew', 'hours_of_rest', NULL, NULL, 0.15),
    ('crew', 'work_order', NULL, NULL, 0.05),
    ('crew', 'note', NULL, NULL, 0.10),

    -- Deckhand biases
    ('deckhand', 'equipment', 'deck', NULL, 0.15),
    ('deckhand', 'work_order', NULL, NULL, 0.10),
    ('deckhand', 'safety', NULL, NULL, 0.15),

    -- Default (no bias)
    ('default', 'default', NULL, NULL, 0.0)
ON CONFLICT (role, lens, doc_type, part_type) DO NOTHING;

-- 3. Add composite index for yacht-scoped queries (if not exists)
CREATE INDEX IF NOT EXISTS ix_si_yacht_obj
    ON search_index (yacht_id, object_type);

CREATE INDEX IF NOT EXISTS ix_si_yacht_updated
    ON search_index (yacht_id, updated_at DESC NULLS LAST);

-- 4. Create f1_search_fusion RPC with deterministic scoring
CREATE OR REPLACE FUNCTION public.f1_search_fusion(
    p_yacht_id uuid,
    p_query_text text,
    p_query_embedding vector(1536) DEFAULT NULL,
    p_role text DEFAULT 'default',
    p_lens text DEFAULT 'default',
    -- Weights
    p_w_text numeric DEFAULT 0.50,
    p_w_vector numeric DEFAULT 0.25,
    p_w_recency numeric DEFAULT 0.15,
    p_w_bias numeric DEFAULT 0.10,
    p_w_rrf numeric DEFAULT 0.20,
    -- Recency decay
    p_lambda numeric DEFAULT 0.01,
    -- RRF constant
    p_rrf_k integer DEFAULT 60,
    -- Logistic transform params for vector sim
    p_logistic_a numeric DEFAULT 6.0,
    p_logistic_b numeric DEFAULT 0.2,
    -- Candidate pool sizes
    p_m_text integer DEFAULT 200,
    p_m_vec integer DEFAULT 200,
    -- Pagination
    p_limit integer DEFAULT 20,
    p_offset integer DEFAULT 0,
    -- Debug mode
    p_debug boolean DEFAULT false
)
RETURNS TABLE(
    object_id uuid,
    object_type text,
    payload jsonb,
    final_score numeric,
    -- Debug fields (only if p_debug=true)
    s_text numeric,
    s_vector numeric,
    s_recency numeric,
    s_bias numeric,
    rank_text bigint,
    rank_vector bigint,
    score numeric,
    rrf_score numeric
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET statement_timeout = '800ms'
AS $$
BEGIN
    RETURN QUERY
    WITH
    -- Text candidate pool (top M_text by ts_rank)
    text_hits AS (
        SELECT
            si.object_id,
            ts_rank(COALESCE(si.tsv_generated, si.tsv), websearch_to_tsquery('english', p_query_text)) AS t_rank
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND COALESCE(si.tsv_generated, si.tsv) @@ websearch_to_tsquery('english', p_query_text)
        ORDER BY t_rank DESC
        LIMIT p_m_text
    ),
    -- Vector candidate pool (top M_vec by cosine similarity)
    vec_hits AS (
        SELECT
            si.object_id,
            (1 - (si.embedding_1536 <=> p_query_embedding))::numeric AS v_sim
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND si.embedding_1536 IS NOT NULL
          AND p_query_embedding IS NOT NULL
        ORDER BY si.embedding_1536 <=> p_query_embedding ASC
        LIMIT p_m_vec
    ),
    -- Union distinct candidates
    candidates AS (
        SELECT DISTINCT object_id FROM (
            SELECT object_id FROM text_hits
            UNION ALL
            SELECT object_id FROM vec_hits
        ) u
    ),
    -- Compute features and ranks
    features AS (
        SELECT
            si.object_id,
            si.object_type,
            si.payload,
            si.updated_at,
            th.t_rank,
            vh.v_sim,
            -- Normalized text score (0-1)
            GREATEST(0, LEAST(1,
                COALESCE(th.t_rank, 0) / NULLIF(MAX(th.t_rank) OVER (), 0)
            ))::numeric AS s_text_raw,
            -- Logistic transformed vector score
            (1.0 / (1.0 + EXP(-p_logistic_a * (COALESCE(vh.v_sim, 0) - p_logistic_b))))::numeric AS s_vector_raw,
            -- Recency score (exponential decay)
            EXP(-p_lambda * GREATEST(0, EXTRACT(EPOCH FROM (NOW() - COALESCE(si.updated_at, NOW() - INTERVAL '1 year'))) / 86400.0))::numeric AS s_recency_raw,
            -- Role bias lookup
            COALESCE(bias.bias, 0.0)::numeric AS s_bias_raw,
            -- Ranks for RRF
            RANK() OVER (ORDER BY COALESCE(th.t_rank, 0) DESC) AS r_text,
            RANK() OVER (ORDER BY COALESCE(vh.v_sim, 0) DESC) AS r_vector
        FROM search_index si
        JOIN candidates c ON c.object_id = si.object_id
        LEFT JOIN text_hits th ON th.object_id = si.object_id
        LEFT JOIN vec_hits vh ON vh.object_id = si.object_id
        LEFT JOIN search_role_bias bias
            ON bias.role = p_role
            AND bias.lens = COALESCE(si.object_type, p_lens)
            AND (bias.doc_type IS NULL OR bias.doc_type = si.payload->>'doc_type')
            AND (bias.part_type IS NULL OR bias.part_type = si.payload->>'part_type')
        WHERE si.yacht_id = p_yacht_id
    ),
    -- Compute final scores
    scored AS (
        SELECT
            f.object_id,
            f.object_type,
            f.payload,
            f.s_text_raw,
            f.s_vector_raw,
            f.s_recency_raw,
            f.s_bias_raw,
            f.r_text,
            f.r_vector,
            -- Weighted sum
            (p_w_text * f.s_text_raw +
             p_w_vector * f.s_vector_raw +
             p_w_recency * f.s_recency_raw +
             p_w_bias * f.s_bias_raw)::numeric AS score_weighted,
            -- RRF score
            ((1.0 / (p_rrf_k + f.r_text)) + (1.0 / (p_rrf_k + f.r_vector)))::numeric AS rrf_contrib,
            -- Final score
            ((p_w_text * f.s_text_raw +
              p_w_vector * f.s_vector_raw +
              p_w_recency * f.s_recency_raw +
              p_w_bias * f.s_bias_raw) +
             p_w_rrf * ((1.0 / (p_rrf_k + f.r_text)) + (1.0 / (p_rrf_k + f.r_vector))))::numeric AS final_score_calc
        FROM features f
    )
    SELECT
        s.object_id,
        s.object_type,
        s.payload,
        s.final_score_calc,
        -- Debug fields (conditionally return)
        CASE WHEN p_debug THEN s.s_text_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.s_vector_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.s_recency_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.s_bias_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.r_text ELSE NULL END,
        CASE WHEN p_debug THEN s.r_vector ELSE NULL END,
        CASE WHEN p_debug THEN s.score_weighted ELSE NULL END,
        CASE WHEN p_debug THEN s.rrf_contrib ELSE NULL END
    FROM scored s
    ORDER BY
        s.final_score_calc DESC,
        s.object_type ASC,
        s.object_id ASC  -- Stable tie-breaker
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

COMMENT ON FUNCTION public.f1_search_fusion IS
    'Deterministic fusion scoring for search results. Combines text, vector, recency, and role bias signals with RRF tie-breaking.';

-- 5. Create simplified wrapper for backward compat
CREATE OR REPLACE FUNCTION public.f1_search_simple(
    p_yacht_id uuid,
    p_query text,
    p_embedding vector(1536) DEFAULT NULL,
    p_limit integer DEFAULT 20
)
RETURNS TABLE(
    object_id uuid,
    object_type text,
    payload jsonb,
    score numeric
)
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
    SELECT
        object_id,
        object_type,
        payload,
        final_score
    FROM f1_search_fusion(
        p_yacht_id,
        p_query,
        p_embedding,
        'default',  -- role
        'default',  -- lens
        0.50,       -- w_text
        0.25,       -- w_vector
        0.15,       -- w_recency
        0.10,       -- w_bias
        0.20,       -- w_rrf
        0.01,       -- lambda
        60,         -- rrf_k
        6.0,        -- logistic_a
        0.2,        -- logistic_b
        200,        -- m_text
        200,        -- m_vec
        p_limit,
        0,          -- offset
        false       -- debug
    );
$$;

-- Verification
DO $$
BEGIN
    RAISE NOTICE 'Migration 030 complete: Deterministic fusion scoring deployed';
    RAISE NOTICE 'Tables: search_role_bias (%s rows)', (SELECT COUNT(*) FROM search_role_bias);
    RAISE NOTICE 'Functions: f1_search_fusion, f1_search_simple';
END $$;
