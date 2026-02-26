-- Migration 45: Add search_text to f1_search_cards return
-- Description: Return search_text for query-time snippet generation
-- Dependencies: 40_create_f1_search_cards.sql
-- Called from: apps/api/routes/f1_search_streaming.py
-- Purpose: Enable Google/Spotlight-style highlighted snippets

-- =============================================================================
-- FUNCTION: f1_search_cards (v2 - with search_text)
-- =============================================================================
-- Change: Added search_text TEXT to RETURNS TABLE
-- Reason: Snippet generation requires raw text at query time

CREATE OR REPLACE FUNCTION public.f1_search_cards(
    p_texts TEXT[],
    p_embeddings VECTOR(1536)[],
    p_org_id UUID,
    p_yacht_id UUID,
    p_rrf_k INT DEFAULT 60,
    p_page_limit INT DEFAULT 20,
    p_trgm_limit REAL DEFAULT 0.15,
    p_object_types TEXT[] DEFAULT NULL
)
RETURNS TABLE(
    object_type TEXT,
    object_id UUID,
    payload JSONB,
    search_text TEXT,           -- NEW: for snippet generation
    fused_score REAL,
    best_rewrite_idx INT,
    ranks JSONB,
    components JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_text TEXT;
    v_embedding VECTOR(1536);
    v_idx INT;
    v_num_rewrites INT;
BEGIN
    v_num_rewrites := LEAST(COALESCE(array_length(p_texts, 1), 0), 3);

    IF v_num_rewrites = 0 THEN
        RETURN;
    END IF;

    -- Temp table now includes search_text
    CREATE TEMP TABLE IF NOT EXISTS _f1_candidates (
        object_type TEXT,
        object_id UUID,
        payload JSONB,
        search_text TEXT,       -- NEW
        rewrite_idx INT,
        trgm_score REAL,
        tsv_score REAL,
        vec_score REAL,
        trgm_rank INT,
        tsv_rank INT,
        vec_rank INT
    ) ON COMMIT DROP;

    TRUNCATE _f1_candidates;

    FOR v_idx IN 1..v_num_rewrites LOOP
        v_text := p_texts[v_idx];
        v_embedding := CASE
            WHEN p_embeddings IS NOT NULL AND array_length(p_embeddings, 1) >= v_idx
            THEN p_embeddings[v_idx]
            ELSE NULL
        END;

        INSERT INTO _f1_candidates (
            object_type, object_id, payload, search_text, rewrite_idx,
            trgm_score, tsv_score, vec_score,
            trgm_rank, tsv_rank, vec_rank
        )
        WITH
        base AS (
            SELECT
                si.object_type,
                si.object_id,
                si.payload,
                si.search_text,
                si.tsv,
                si.embedding_1536
            FROM public.search_index si
            WHERE (p_yacht_id IS NULL OR si.yacht_id = p_yacht_id)
              AND (p_org_id IS NULL OR si.org_id = p_org_id)
              AND (p_object_types IS NULL OR si.object_type = ANY(p_object_types))
        ),

        trgm AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                b.search_text,          -- NEW
                similarity(b.search_text, v_text) AS score
            FROM base b
            WHERE v_text IS NOT NULL
              AND v_text <> ''
              AND b.search_text IS NOT NULL
              AND b.search_text % v_text
              AND similarity(b.search_text, v_text) >= p_trgm_limit
            ORDER BY similarity(b.search_text, v_text) DESC
            LIMIT 100
        ),
        trgm_ranked AS (
            SELECT t.*, ROW_NUMBER() OVER (ORDER BY t.score DESC) AS rank
            FROM trgm t
        ),

        tsv AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                b.search_text,          -- NEW
                ts_rank_cd(b.tsv, plainto_tsquery('english', v_text)) AS score
            FROM base b
            WHERE v_text IS NOT NULL
              AND v_text <> ''
              AND b.tsv @@ plainto_tsquery('english', v_text)
            ORDER BY ts_rank_cd(b.tsv, plainto_tsquery('english', v_text)) DESC
            LIMIT 100
        ),
        tsv_ranked AS (
            SELECT t.*, ROW_NUMBER() OVER (ORDER BY t.score DESC) AS rank
            FROM tsv t
        ),

        vec AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                b.search_text,          -- NEW
                (1.0 - (b.embedding_1536 <=> v_embedding)) AS score
            FROM base b
            WHERE v_embedding IS NOT NULL
              AND b.embedding_1536 IS NOT NULL
            ORDER BY b.embedding_1536 <=> v_embedding
            LIMIT 100
        ),
        vec_ranked AS (
            SELECT v.*, ROW_NUMBER() OVER (ORDER BY v.score DESC) AS rank
            FROM vec v
        ),

        merged AS (
            SELECT
                COALESCE(tr.object_type, tv.object_type, vr.object_type) AS object_type,
                COALESCE(tr.object_id, tv.object_id, vr.object_id) AS object_id,
                COALESCE(tr.payload, tv.payload, vr.payload) AS payload,
                COALESCE(tr.search_text, tv.search_text, vr.search_text) AS search_text,  -- NEW
                COALESCE(tr.score, 0) AS trgm_score,
                COALESCE(tv.score, 0) AS tsv_score,
                COALESCE(vr.score, 0) AS vec_score,
                tr.rank AS trgm_rank,
                tv.rank AS tsv_rank,
                vr.rank AS vec_rank
            FROM trgm_ranked tr
            FULL OUTER JOIN tsv_ranked tv
                ON tr.object_type = tv.object_type AND tr.object_id = tv.object_id
            FULL OUTER JOIN vec_ranked vr
                ON COALESCE(tr.object_type, tv.object_type) = vr.object_type
               AND COALESCE(tr.object_id, tv.object_id) = vr.object_id
        )
        SELECT
            m.object_type,
            m.object_id,
            m.payload,
            m.search_text,              -- NEW
            v_idx,
            m.trgm_score,
            m.tsv_score,
            m.vec_score,
            m.trgm_rank,
            m.tsv_rank,
            m.vec_rank
        FROM merged m
        WHERE m.trgm_score > 0 OR m.tsv_score > 0 OR m.vec_score > 0;

    END LOOP;

    RETURN QUERY
    WITH
    best_per_object AS (
        SELECT
            c.object_type,
            c.object_id,
            c.payload,
            c.search_text,              -- NEW
            c.rewrite_idx,
            c.trgm_score,
            c.tsv_score,
            c.vec_score,
            c.trgm_rank,
            c.tsv_rank,
            c.vec_rank,
            (
                CASE WHEN c.trgm_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.trgm_rank) ELSE 0 END +
                CASE WHEN c.tsv_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.tsv_rank) ELSE 0 END +
                CASE WHEN c.vec_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.vec_rank) ELSE 0 END
            )::REAL AS rrf_score,
            ROW_NUMBER() OVER (
                PARTITION BY c.object_type, c.object_id
                ORDER BY (
                    CASE WHEN c.trgm_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.trgm_rank) ELSE 0 END +
                    CASE WHEN c.tsv_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.tsv_rank) ELSE 0 END +
                    CASE WHEN c.vec_rank IS NOT NULL THEN 1.0 / (p_rrf_k + c.vec_rank) ELSE 0 END
                ) DESC
            ) AS rn
        FROM _f1_candidates c
    ),
    best AS (
        SELECT * FROM best_per_object WHERE rn = 1
    )
    SELECT
        b.object_type,
        b.object_id,
        b.payload,
        b.search_text,                  -- NEW
        b.rrf_score AS fused_score,
        b.rewrite_idx AS best_rewrite_idx,
        jsonb_build_object(
            'trigram', b.trgm_rank,
            'tsv', b.tsv_rank,
            'vector', b.vec_rank
        ) AS ranks,
        jsonb_build_object(
            'trigram', ROUND(b.trgm_score::NUMERIC, 4),
            'tsv', ROUND(b.tsv_score::NUMERIC, 4),
            'vector', ROUND(b.vec_score::NUMERIC, 4)
        ) AS components
    FROM best b
    ORDER BY b.rrf_score DESC
    LIMIT p_page_limit;

END;
$$;

-- =============================================================================
-- GRANTS (unchanged - function signature changed but name same)
-- =============================================================================
GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO service_role;

GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO authenticated;

COMMENT ON FUNCTION public.f1_search_cards IS
'F1 Search hybrid search using RRF (Reciprocal Rank Fusion).
v2: Now returns search_text for snippet generation.
Parameters unchanged from v1.
Returns: object_type, object_id, payload, search_text, fused_score, best_rewrite_idx, ranks, components';
