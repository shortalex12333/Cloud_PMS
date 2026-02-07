--
-- Fix match_link_targets_v2 RPC
-- 1. Use embedding_1536 (not embedding) - matches embedding_worker_1536 output
-- 2. Use websearch_to_tsquery (not plainto_tsquery) - better UX for human queries
--

CREATE OR REPLACE FUNCTION public.match_link_targets_v2(
    p_yacht_id uuid,
    p_query text,
    p_query_embedding vector(1536),
    p_object_types text[] DEFAULT NULL,
    p_role text DEFAULT NULL,
    p_days_back int DEFAULT 365,
    p_text_k int DEFAULT 300,
    p_vector_k int DEFAULT 300,
    p_min_vector float DEFAULT 0.60
)
RETURNS TABLE(
    object_type text,
    object_id uuid,
    label text,
    s_text float,
    s_vector float,
    s_recency float,
    s_bias float,
    rank_text int,
    rank_vector int
)
LANGUAGE sql
SECURITY DEFINER
AS $$
WITH base AS (
    SELECT si.object_type,
           si.object_id,
           COALESCE(si.payload->>'label', si.payload->>'title', si.search_text) AS label,
           si.tsv,
           si.embedding_1536,  -- FIXED: use 1536-dim column
           si.updated_at
    FROM public.search_index si
    WHERE si.yacht_id = p_yacht_id
      AND (p_object_types IS NULL OR si.object_type = ANY(p_object_types))
      AND si.updated_at >= NOW() - (p_days_back || ' days')::interval
),
txt AS (
    SELECT b.object_type, b.object_id, b.label,
           -- S_text: clamped ts_rank_cd
           GREATEST(0.0, LEAST(1.0, ts_rank_cd(b.tsv, websearch_to_tsquery('english', p_query)))) AS s_text,
           b.updated_at
    FROM base b
    WHERE (p_query IS NOT NULL AND p_query <> '')
      AND b.tsv @@ websearch_to_tsquery('english', p_query)  -- FIXED: websearch_to_tsquery
    ORDER BY ts_rank_cd(b.tsv, websearch_to_tsquery('english', p_query)) DESC
    LIMIT p_text_k
),
vec AS (
    SELECT b.object_type, b.object_id, b.label,
           (1 - (b.embedding_1536 <=> p_query_embedding)) AS s_vector,  -- FIXED: use 1536-dim
           b.updated_at
    FROM base b
    WHERE p_query_embedding IS NOT NULL
      AND b.embedding_1536 IS NOT NULL  -- FIXED: use 1536-dim
    ORDER BY b.embedding_1536 <=> p_query_embedding  -- FIXED: use 1536-dim
    LIMIT p_vector_k
),
merged AS (
    SELECT
        COALESCE(t.object_type, v.object_type) AS object_type,
        COALESCE(t.object_id, v.object_id) AS object_id,
        COALESCE(t.label, v.label) AS label,
        COALESCE(t.s_text, 0.0) AS s_text,
        COALESCE(v.s_vector, 0.0) AS s_vector,
        COALESCE(t.updated_at, v.updated_at) AS updated_at
    FROM txt t
    FULL OUTER JOIN vec v
        ON t.object_type = v.object_type
       AND t.object_id = v.object_id
),
scored AS (
    SELECT
        m.*,
        -- S_recency: 90-day half-life exponential decay
        EXP(-(LN(2)/90.0) * EXTRACT(EPOCH FROM (NOW() - m.updated_at))/86400.0) AS s_recency
    FROM merged m
    -- Allow either text or vector to carry the candidate
    WHERE (m.s_text > 0.0) OR (m.s_vector >= p_min_vector)
),
with_bias AS (
    SELECT
        s.*,
        -- Role bias: legacy shim (doc_type, bias) until schema migration
        GREATEST(0.0, LEAST(1.0,
            COALESCE(NULLIF(b.bias::text,'')::float, 0.0)
        )) AS s_bias
    FROM scored s
    LEFT JOIN public.search_role_bias b
        ON (p_role IS NOT NULL AND b.role = p_role)
       AND (b.doc_type IS NOT NULL AND
            (CASE
                WHEN b.doc_type IN ('work_order','wo') THEN 'work_order'
                WHEN b.doc_type IN ('equipment','asset') THEN 'equipment'
                WHEN b.doc_type IN ('part','component') THEN 'part'
                ELSE b.doc_type
            END) = s.object_type)
),
ranked AS (
    SELECT
        wb.*,
        DENSE_RANK() OVER (ORDER BY wb.s_text DESC NULLS LAST)   AS rank_text,
        DENSE_RANK() OVER (ORDER BY wb.s_vector DESC NULLS LAST) AS rank_vector
    FROM with_bias wb
)
SELECT object_type, object_id, label,
       s_text, s_vector, s_recency, s_bias,
       rank_text, rank_vector
FROM ranked;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.match_link_targets_v2 TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_link_targets_v2 TO service_role;

-- Update comment
COMMENT ON FUNCTION public.match_link_targets_v2 IS
'V2.1: Uses embedding_1536 column (matches embedding_worker_1536) and websearch_to_tsquery for better text UX.
FULL OUTER JOIN of text ∪ vector candidates. Filters by (s_text > 0 OR s_vector >= p_min_vector).';
