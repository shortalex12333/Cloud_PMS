-- Migration 51: Fix pg_trgm threshold in f1_search_cards
--
-- Problem: The f1_search_cards function uses the % operator which respects
-- the session-level pg_trgm.similarity_threshold (default 0.3). Short queries
-- like "show WOs" have similarity < 0.3 against long search_text, causing
-- zero matches even though the p_trgm_limit parameter is set lower.
--
-- Solution: Set the threshold at the start of the function, then restore it.
--
-- Evidence:
--   - similarity('show WOs', <any work_order>) ≈ 0.045 (below 0.3 threshold)
--   - After set_limit(0.05), search_text % 'show WOs' returns 7,470 matches
--   - The p_trgm_limit parameter (default 0.15) only affects the final filter,
--     not the % operator used by the GiST index
--

-- =============================================================================
-- PATCH: f1_search_cards - Add threshold setting
-- =============================================================================

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
    v_old_limit REAL;
BEGIN
    -- PATCH: Save and set pg_trgm threshold to match p_trgm_limit
    -- This ensures short queries can match via the % operator
    v_old_limit := show_limit();
    PERFORM set_limit(LEAST(p_trgm_limit, 0.1));  -- Cap at 0.1 to avoid too much noise

    -- Get number of rewrites (max 3)
    v_num_rewrites := LEAST(COALESCE(array_length(p_texts, 1), 0), 3);

    -- Early exit if no queries
    IF v_num_rewrites = 0 THEN
        PERFORM set_limit(v_old_limit);  -- Restore before return
        RETURN;
    END IF;

    -- Create temp table to accumulate per-rewrite results
    CREATE TEMP TABLE IF NOT EXISTS _f1_candidates (
        object_type TEXT,
        object_id UUID,
        payload JSONB,
        rewrite_idx INT,
        trgm_score REAL,
        tsv_score REAL,
        vec_score REAL,
        trgm_rank INT,
        tsv_rank INT,
        vec_rank INT
    ) ON COMMIT DROP;

    -- Truncate in case of reuse within same transaction
    TRUNCATE _f1_candidates;

    -- Process each rewrite
    FOR v_idx IN 1..v_num_rewrites LOOP
        v_text := p_texts[v_idx];
        v_embedding := CASE
            WHEN p_embeddings IS NOT NULL AND array_length(p_embeddings, 1) >= v_idx
            THEN p_embeddings[v_idx]
            ELSE NULL
        END;

        -- Insert candidates from this rewrite
        INSERT INTO _f1_candidates (
            object_type, object_id, payload, rewrite_idx,
            trgm_score, tsv_score, vec_score,
            trgm_rank, tsv_rank, vec_rank
        )
        WITH
        -- Base filter: yacht/org scope + object type filter
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

        -- Trigram similarity candidates
        trgm AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                similarity(b.search_text, v_text) AS score
            FROM base b
            WHERE v_text IS NOT NULL
              AND v_text <> ''
              AND b.search_text IS NOT NULL
              AND b.search_text % v_text  -- Uses session-level threshold (now lowered)
              AND similarity(b.search_text, v_text) >= p_trgm_limit
            ORDER BY similarity(b.search_text, v_text) DESC
            LIMIT 100
        ),
        trgm_ranked AS (
            SELECT
                t.*,
                ROW_NUMBER() OVER (ORDER BY t.score DESC) AS rank
            FROM trgm t
        ),

        -- Full-text search candidates
        tsv AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                ts_rank_cd(b.tsv, plainto_tsquery('english', v_text)) AS score
            FROM base b
            WHERE v_text IS NOT NULL
              AND v_text <> ''
              AND b.tsv @@ plainto_tsquery('english', v_text)
            ORDER BY ts_rank_cd(b.tsv, plainto_tsquery('english', v_text)) DESC
            LIMIT 100
        ),
        tsv_ranked AS (
            SELECT
                t.*,
                ROW_NUMBER() OVER (ORDER BY t.score DESC) AS rank
            FROM tsv t
        ),

        -- Vector similarity candidates
        vec AS (
            SELECT
                b.object_type,
                b.object_id,
                b.payload,
                (1.0 - (b.embedding_1536 <=> v_embedding)) AS score
            FROM base b
            WHERE v_embedding IS NOT NULL
              AND b.embedding_1536 IS NOT NULL
            ORDER BY b.embedding_1536 <=> v_embedding
            LIMIT 100
        ),
        vec_ranked AS (
            SELECT
                v.*,
                ROW_NUMBER() OVER (ORDER BY v.score DESC) AS rank
            FROM vec v
        ),

        -- Full outer join all three sources
        merged AS (
            SELECT
                COALESCE(tr.object_type, tv.object_type, vr.object_type) AS object_type,
                COALESCE(tr.object_id, tv.object_id, vr.object_id) AS object_id,
                COALESCE(tr.payload, tv.payload, vr.payload) AS payload,
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

    -- PATCH: Restore original threshold
    PERFORM set_limit(v_old_limit);

    -- Aggregate across rewrites and compute RRF fusion
    RETURN QUERY
    WITH
    -- For each (object_type, object_id), pick the best rewrite
    best_per_object AS (
        SELECT
            c.object_type,
            c.object_id,
            c.payload,
            c.rewrite_idx,
            c.trgm_score,
            c.tsv_score,
            c.vec_score,
            c.trgm_rank,
            c.tsv_rank,
            c.vec_rank,
            -- RRF score: sum of 1/(k+rank) for each signal
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
-- VERIFICATION
-- =============================================================================

-- Test that short queries now work
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM f1_search_cards(
        ARRAY['show WOs']::text[],
        NULL::vector(1536)[],
        NULL::uuid,
        '85fe1119-b04c-41ac-80f1-829d23322598'::uuid,
        60, 10, 0.05, NULL::text[]
    );

    IF v_count > 0 THEN
        RAISE NOTICE 'SUCCESS: Short query "show WOs" now returns % results', v_count;
    ELSE
        RAISE WARNING 'FAILED: Short query "show WOs" still returns 0 results';
    END IF;
END;
$$;

COMMENT ON FUNCTION public.f1_search_cards IS
'F1 Search hybrid search using RRF (Reciprocal Rank Fusion) across trigram, full-text, and vector similarity.
PATCHED (migration 51): Now sets pg_trgm.similarity_threshold internally to support short queries.
Accepts multiple query rewrites, returns deduplicated results with fused scores.';
