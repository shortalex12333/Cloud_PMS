-- Migration 009: Inline Trigram Limit
-- Adds trgm_limit parameter to hyper_search_multi to eliminate extra round-trip
-- Each DB call to Supabase adds ~200-300ms network latency

-- Drop old 6-arg version to avoid ambiguity
DROP FUNCTION IF EXISTS hyper_search_multi(text[], vector(1536)[], uuid, uuid, int, int);

CREATE OR REPLACE FUNCTION hyper_search_multi(
    rewrite_texts text[],
    rewrite_embeddings vector(1536)[],
    filter_org_id uuid,
    filter_yacht_id uuid,
    rrf_k int DEFAULT 60,
    page_limit int DEFAULT 20,
    trgm_limit real DEFAULT 0.15  -- New: trigram similarity threshold
) RETURNS TABLE (
    object_type text,
    object_id uuid,
    payload jsonb,
    fused_score double precision,
    best_rewrite_idx int,
    ranks jsonb,
    components jsonb
) SECURITY INVOKER LANGUAGE plpgsql AS $$
BEGIN
    -- Set trigram threshold inside function to eliminate extra round-trip
    PERFORM set_limit(trgm_limit);

    RETURN QUERY
    WITH rewrites AS (
        SELECT generate_subscripts(rewrite_texts,1) AS idx,
               rewrite_texts[generate_subscripts(rewrite_texts,1)] AS q,
               rewrite_embeddings[generate_subscripts(rewrite_embeddings,1)] AS v
    ),
    trigram AS (
        SELECT r.idx, s.object_type, s.object_id,
               similarity(s.search_text, r.q) AS score,
               row_number() OVER (PARTITION BY r.idx ORDER BY similarity(s.search_text, r.q) DESC) AS rank,
               'trigram'::text AS source
        FROM rewrites r
        JOIN search_index s
          ON s.org_id = filter_org_id
         AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
        WHERE s.search_text % r.q
    ),
    fts AS (
        SELECT r.idx, s.object_type, s.object_id,
               ts_rank(s.tsv, websearch_to_tsquery('english', r.q)) AS score,
               row_number() OVER (PARTITION BY r.idx ORDER BY ts_rank(s.tsv, websearch_to_tsquery('english', r.q)) DESC) AS rank,
               'fts'::text AS source
        FROM rewrites r
        JOIN search_index s
          ON s.org_id = filter_org_id
         AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
    ),
    vec AS (
        SELECT r.idx, s.object_type, s.object_id,
               CASE WHEN r.v IS NULL THEN NULL ELSE 1 - (s.embedding <=> r.v) END AS score,
               CASE WHEN r.v IS NULL THEN NULL ELSE row_number() OVER (PARTITION BY r.idx ORDER BY s.embedding <=> r.v ASC) END AS rank,
               'vector'::text AS source
        FROM rewrites r
        JOIN search_index s
          ON s.org_id = filter_org_id
         AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
        WHERE s.embedding IS NOT NULL
    ),
    all_results AS (
        SELECT * FROM (SELECT * FROM trigram LIMIT 50) t
        UNION ALL
        SELECT * FROM (SELECT * FROM fts LIMIT 50) f
        UNION ALL
        SELECT * FROM (SELECT * FROM vec LIMIT 80) v
    ),
    aggregated AS (
        SELECT a.idx, a.object_type, a.object_id,
               MIN(CASE WHEN a.source = 'trigram' THEN a.rank END) AS trigram_rank,
               MIN(CASE WHEN a.source = 'fts' THEN a.rank END) AS fts_rank,
               MIN(CASE WHEN a.source = 'vector' THEN a.rank END) AS vector_rank,
               MAX(CASE WHEN a.source = 'trigram' THEN a.score END) AS trigram_score,
               MAX(CASE WHEN a.source = 'fts' THEN a.score END) AS fts_score,
               MAX(CASE WHEN a.source = 'vector' THEN a.score END) AS vector_sim
        FROM all_results a
        GROUP BY a.idx, a.object_type, a.object_id
    )
    SELECT a.object_type, a.object_id, COALESCE(s.payload, '{}'::jsonb) AS payload,
           (COALESCE(1.0/(rrf_k + a.trigram_rank),0) +
            COALESCE(1.0/(rrf_k + a.fts_rank),0) +
            COALESCE(1.0/(rrf_k + a.vector_rank),0))::double precision AS fused_score,
           (array_agg(a.idx ORDER BY
               COALESCE(1.0/(rrf_k + a.trigram_rank),0) +
               COALESCE(1.0/(rrf_k + a.fts_rank),0) +
               COALESCE(1.0/(rrf_k + a.vector_rank),0) DESC))[1] AS best_rewrite_idx,
           jsonb_build_object('trigram', a.trigram_rank, 'fts', a.fts_rank, 'vector', a.vector_rank) AS ranks,
           jsonb_build_object('trigram', a.trigram_score, 'fts', a.fts_score, 'vector', a.vector_sim) AS components
    FROM aggregated a
    LEFT JOIN search_index s
      ON s.object_type = a.object_type AND s.object_id = a.object_id
    GROUP BY a.object_type, a.object_id, s.payload, a.trigram_rank, a.fts_rank, a.vector_rank, a.trigram_score, a.fts_score, a.vector_sim
    ORDER BY fused_score DESC
    LIMIT page_limit;
END;
$$;

COMMENT ON FUNCTION hyper_search_multi(text[], vector(1536)[], uuid, uuid, int, int, real) IS 'Hybrid search with RRF fusion. Includes inline set_limit() to eliminate extra round-trip. Vector cap: 80.';
