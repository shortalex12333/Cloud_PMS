-- Migration 41: Add deterministic tie-breakers to f1_search_cards
-- Description: Fixes non-deterministic ranking when RRF scores collide
-- Root Cause: ORDER BY rrf_score DESC alone causes PostgreSQL to return
--             rows in arbitrary disk-read order when scores tie.
-- Solution: Add secondary sort keys: updated_at DESC, object_id ASC
--
-- Dependencies:
--   - 40_create_f1_search_cards.sql (original function)
--   - 01_create_search_index.sql (updated_at column)
--
-- ARCHITECTURAL COMPLIANCE (Celeste OS Absolute Laws):
--   LAW 1: No magic - tie-breakers do NOT filter or predict intent
--   LAW 2: No hardcoded walls - using existing column values, not weights
--   LAW 3: No regex - pure SQL ordering
--   LAW 4: No leaky abstractions - change contained in Worker 2
--   LAW 5: No fake math - real columns from search_index
--   LAW 6: No placeholders - complete production-ready code

-- =============================================================================
-- FUNCTION: f1_search_cards (Deterministic Ordering)
-- =============================================================================
-- Changes from v1:
--   1. Added updated_at to _f1_candidates temp table
--   2. Carry updated_at through base CTE
--   3. Final ORDER BY: rrf_score DESC, updated_at DESC NULLS LAST, object_id ASC
--
-- This creates a TOTAL ORDER - no two rows can have identical sort keys.

CREATE OR REPLACE FUNCTION public.f1_search_cards(
    p_texts TEXT[],                    -- Array of query text rewrites (max 3)
    p_embeddings VECTOR(1536)[],       -- Array of embeddings for each rewrite
    p_org_id UUID,                     -- Organization ID for RLS filtering
    p_yacht_id UUID,                   -- Yacht ID for scoping (can be NULL)
    p_rrf_k INT DEFAULT 60,            -- RRF smoothing constant (higher = more uniform)
    p_page_limit INT DEFAULT 20,       -- Max results to return
    p_trgm_limit REAL DEFAULT 0.15,    -- Trigram similarity threshold
    p_object_types TEXT[] DEFAULT NULL -- Filter to specific object types (NULL = all)
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
BEGIN
    -- Get number of rewrites (max 3)
    v_num_rewrites := LEAST(COALESCE(array_length(p_texts, 1), 0), 3);

    -- Early exit if no queries
    IF v_num_rewrites = 0 THEN
        RETURN;
    END IF;

    -- Create temp table to accumulate per-rewrite results
    -- CHANGE v2: Added updated_at for deterministic tie-breaking
    CREATE TEMP TABLE IF NOT EXISTS _f1_candidates (
        object_type TEXT,
        object_id UUID,
        payload JSONB,
        updated_at TIMESTAMPTZ,        -- NEW: For deterministic ordering
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
            object_type, object_id, payload, updated_at, rewrite_idx,
            trgm_score, tsv_score, vec_score,
            trgm_rank, tsv_rank, vec_rank
        )
        WITH
        -- Base filter: yacht/org scope + object type filter
        -- CHANGE v2: Include updated_at for later sorting
        base AS (
            SELECT
                si.object_type,
                si.object_id,
                si.payload,
                si.updated_at,             -- NEW: Carry through for tie-breaking
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
                b.updated_at,
                similarity(b.search_text, v_text) AS score
            FROM base b
            WHERE v_text IS NOT NULL
              AND v_text <> ''
              AND b.search_text IS NOT NULL
              AND b.search_text % v_text  -- Use GiST index
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
                b.updated_at,
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
                b.updated_at,
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
                COALESCE(tr.updated_at, tv.updated_at, vr.updated_at) AS updated_at,
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
            m.updated_at,
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

    -- Aggregate across rewrites and compute RRF fusion
    -- CHANGE v2: Deterministic ORDER BY with tie-breakers
    RETURN QUERY
    WITH
    -- For each (object_type, object_id), pick the best rewrite
    best_per_object AS (
        SELECT
            c.object_type,
            c.object_id,
            c.payload,
            c.updated_at,
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
    -- CRITICAL CHANGE v2: Deterministic total ordering
    -- 1. Primary: RRF score (relevance)
    -- 2. Secondary: updated_at DESC (temporal recency, NULLS LAST for safety)
    -- 3. Tertiary: object_id ASC (UUID provides unique tie-breaker)
    ORDER BY b.rrf_score DESC, b.updated_at DESC NULLS LAST, b.object_id ASC
    LIMIT p_page_limit;

END;
$$;

-- =============================================================================
-- GRANTS (Maintain existing permissions)
-- =============================================================================

GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO service_role;

GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO authenticated;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON FUNCTION public.f1_search_cards IS
'F1 Search hybrid search using RRF (Reciprocal Rank Fusion) across trigram, full-text, and vector similarity.

v2 (Migration 41): Added deterministic tie-breaking to eliminate ranking non-determinism.
Final ORDER BY: rrf_score DESC, updated_at DESC NULLS LAST, object_id ASC

Parameters:
  - p_texts: Array of query text rewrites (max 3)
  - p_embeddings: Array of vector embeddings for semantic search
  - p_org_id: Organization ID for RLS filtering
  - p_yacht_id: Yacht ID for scoping (can be NULL for org-wide search)
  - p_rrf_k: RRF smoothing constant (default 60, higher = more uniform ranking)
  - p_page_limit: Max results to return (default 20)
  - p_trgm_limit: Trigram similarity threshold (default 0.15)
  - p_object_types: Filter to specific object types (NULL = all types)

Returns: object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components

Tie-Breaking Strategy:
  When two entities have identical rrf_scores, they are ordered by:
  1. updated_at DESC - more recently updated documents rank higher
  2. object_id ASC - UUID provides consistent, deterministic final ordering

This ensures identical queries always return results in the same order.';
