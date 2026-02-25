-- Migration: 20260225_003_f1_search_cards_rpc.sql
-- Purpose: Add f1_search_cards RPC for hybrid search (trigram + FTS + vector)
-- Date: 2026-02-25
--
-- ROOT CAUSE FIX: This function existed in database/migrations/ but was
-- missing from supabase/migrations/, causing F1 semantic search to fail.
-- Without this function, the F1 search endpoint cannot execute hybrid queries.
--
-- Dependencies:
--   - search_index table with embedding_1536 column
--   - pgvector extension
--   - pg_trgm extension

-- Ensure required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- FUNCTION: f1_search_cards (Deterministic Ordering v2)
-- =============================================================================
-- Hybrid search across search_index using Reciprocal Rank Fusion (RRF) of:
--   1. Trigram similarity (pg_trgm) - fuzzy text matching
--   2. Full-text search (tsvector) - keyword/phrase matching
--   3. Vector similarity (pgvector) - semantic matching
--
-- Accepts multiple rewrite queries and embeddings, fuses results across all.
-- Returns deduplicated results ranked by fused RRF score.
--
-- v2: Added deterministic tie-breaking to eliminate ranking non-determinism.
-- Final ORDER BY: rrf_score DESC, updated_at DESC NULLS LAST, object_id ASC

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
    -- v2: Added updated_at for deterministic tie-breaking
    CREATE TEMP TABLE IF NOT EXISTS _f1_candidates (
        object_type TEXT,
        object_id UUID,
        payload JSONB,
        updated_at TIMESTAMPTZ,        -- For deterministic ordering
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
        -- Include updated_at for later sorting
        base AS (
            SELECT
                si.object_type,
                si.object_id,
                si.payload,
                si.updated_at,
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

        -- Vector similarity candidates (SEMANTIC SEARCH - LAW 21)
        -- This is where "thing that makes drinking water" finds "Watermaker"
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
    -- Deterministic ORDER BY with tie-breakers
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
    -- DETERMINISTIC TOTAL ORDERING:
    -- 1. Primary: RRF score (relevance)
    -- 2. Secondary: updated_at DESC (temporal recency, NULLS LAST for safety)
    -- 3. Tertiary: object_id ASC (UUID provides unique tie-breaker)
    ORDER BY b.rrf_score DESC, b.updated_at DESC NULLS LAST, b.object_id ASC
    LIMIT p_page_limit;

END;
$$;

-- =============================================================================
-- GRANTS
-- =============================================================================

-- Grant execute to service role (backend API)
GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO service_role;

-- Grant to authenticated users for direct RPC calls
GRANT EXECUTE ON FUNCTION public.f1_search_cards(
    TEXT[], VECTOR(1536)[], UUID, UUID, INT, INT, REAL, TEXT[]
) TO authenticated;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON FUNCTION public.f1_search_cards IS
'F1 Search hybrid search using RRF (Reciprocal Rank Fusion) across trigram, full-text, and vector similarity.

ROOT CAUSE FIX: This migration adds the f1_search_cards function that was missing from
supabase/migrations/, causing semantic search to fail in production.

Accepts multiple query rewrites, returns deduplicated results with fused scores.
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

LAW 21 Compliance: Vector search queries search_index.embedding_1536 (Storefront),
NOT pms_* tables (Warehouse). This enables semantic matching like
"thing that makes drinking water" → "Watermaker/Desalinator".';

-- =============================================================================
-- INDEX RECOMMENDATIONS (Ensure these exist for optimal performance)
-- =============================================================================

-- Trigram GiST index for fuzzy matching
CREATE INDEX IF NOT EXISTS idx_search_index_search_text_trgm
    ON public.search_index USING GIST (search_text gist_trgm_ops);

-- GIN index for full-text search (tsv column)
CREATE INDEX IF NOT EXISTS idx_search_index_tsv
    ON public.search_index USING GIN (tsv);

-- HNSW index for vector similarity (fast ANN)
-- Note: HNSW is preferred over IVFFlat for better recall
CREATE INDEX IF NOT EXISTS idx_search_index_embedding_1536_hnsw
    ON public.search_index USING hnsw (embedding_1536 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- B-tree indexes for filtering
CREATE INDEX IF NOT EXISTS idx_search_index_yacht_id
    ON public.search_index (yacht_id);

CREATE INDEX IF NOT EXISTS idx_search_index_org_id
    ON public.search_index (org_id);

CREATE INDEX IF NOT EXISTS idx_search_index_object_type
    ON public.search_index (object_type);
