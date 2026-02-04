-- Migration: Switch to OpenAI text-embedding-3-small (1536 dimensions)
-- This migration changes the embedding column from 384-d to 1536-d

-- 0) Drop vector index before altering type
DROP INDEX IF EXISTS ix_search_vector;

-- 1) Change vector column to 1536 dims
ALTER TABLE search_index
ALTER COLUMN embedding TYPE vector(1536)
USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::vector(1536) END);

-- 2) Recreate HNSW index for 1536 dims
CREATE INDEX ix_search_vector ON search_index
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- 3) Update RPC signatures to 1536
CREATE OR REPLACE FUNCTION hyper_search(
    query_text text,
    query_embedding vector(1536),
    filter_org_id uuid,
    filter_yacht_id uuid,
    rrf_k int DEFAULT 60,
    page_limit int DEFAULT 20
) RETURNS TABLE (
    object_type text,
    object_id uuid,
    payload jsonb,
    fused_score double precision,
    ranks jsonb,
    components jsonb
) SECURITY INVOKER LANGUAGE sql AS $$
SELECT object_type, object_id, payload,
       (COALESCE(1.0/(rrf_k + trigram_rank),0) +
        COALESCE(1.0/(rrf_k + fts_rank),0) +
        COALESCE(1.0/(rrf_k + vector_rank),0)) AS fused_score,
       jsonb_build_object('trigram', trigram_rank,'fts', fts_rank,'vector', vector_rank) AS ranks,
       jsonb_build_object('trigram', trigram_score,'fts', fts_score,'vector', vector_sim) AS components
FROM (
    WITH
    trigram AS (
        SELECT object_type, object_id,
               similarity(search_text, query_text) AS trigram_score,
               row_number() OVER (ORDER BY similarity(search_text, query_text) DESC) AS trigram_rank
        FROM search_index
        WHERE org_id = filter_org_id
          AND (filter_yacht_id IS NULL OR yacht_id = filter_yacht_id)
          AND search_text % query_text
        LIMIT 50
    ),
    fts AS (
        SELECT object_type, object_id,
               ts_rank(tsv, websearch_to_tsquery('english', query_text)) AS fts_score,
               row_number() OVER (ORDER BY ts_rank(tsv, websearch_to_tsquery('english', query_text)) DESC) AS fts_rank
        FROM search_index
        WHERE org_id = filter_org_id
          AND (filter_yacht_id IS NULL OR yacht_id = filter_yacht_id)
        LIMIT 50
    ),
    vec AS (
        SELECT object_type, object_id,
               1 - (embedding <=> query_embedding) AS vector_sim,
               row_number() OVER (ORDER BY embedding <=> query_embedding ASC) AS vector_rank
        FROM search_index
        WHERE org_id = filter_org_id
          AND (filter_yacht_id IS NULL OR yacht_id = filter_yacht_id)
          AND embedding IS NOT NULL
        ORDER BY embedding <=> query_embedding ASC
        LIMIT 100
    )
    SELECT COALESCE(t.object_type, f.object_type, v.object_type) AS object_type,
           COALESCE(t.object_id, f.object_id, v.object_id) AS object_id,
           COALESCE(si.payload, '{}'::jsonb) AS payload,
           MIN(t.trigram_rank) AS trigram_rank,
           MIN(f.fts_rank) AS fts_rank,
           MIN(v.vector_rank) AS vector_rank,
           MAX(t.trigram_score) AS trigram_score,
           MAX(f.fts_score) AS fts_score,
           MAX(v.vector_sim) AS vector_sim
    FROM (SELECT * FROM trigram
          UNION ALL
          SELECT * FROM fts
          UNION ALL
          SELECT * FROM vec) u
    LEFT JOIN trigram t USING (object_type, object_id)
    LEFT JOIN fts     f USING (object_type, object_id)
    LEFT JOIN vec     v USING (object_type, object_id)
    LEFT JOIN search_index si USING (object_type, object_id)
    GROUP BY 1,2,3
) s
ORDER BY fused_score DESC
LIMIT page_limit;
$$;

CREATE OR REPLACE FUNCTION hyper_search_multi(
    rewrite_texts text[],
    rewrite_embeddings vector(1536)[],
    filter_org_id uuid,
    filter_yacht_id uuid,
    rrf_k int DEFAULT 60,
    page_limit int DEFAULT 20
) RETURNS TABLE (
    object_type text,
    object_id uuid,
    payload jsonb,
    fused_score double precision,
    best_rewrite_idx int,
    ranks jsonb,
    components jsonb
) SECURITY INVOKER LANGUAGE sql AS $$
WITH rewrites AS (
    SELECT generate_subscripts(rewrite_texts,1) AS idx,
           rewrite_texts[generate_subscripts(rewrite_texts,1)] AS q,
           rewrite_embeddings[generate_subscripts(rewrite_embeddings,1)] AS v
),
trigram AS (
    SELECT r.idx, s.object_type, s.object_id,
           similarity(s.search_text, r.q) AS trigram_score,
           row_number() OVER (PARTITION BY r.idx ORDER BY similarity(s.search_text, r.q) DESC) AS trigram_rank
    FROM rewrites r
    JOIN search_index s
      ON s.org_id = filter_org_id
     AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
    WHERE s.search_text % r.q
    LIMIT 50
),
fts AS (
    SELECT r.idx, s.object_type, s.object_id,
           ts_rank(s.tsv, websearch_to_tsquery('english', r.q)) AS fts_score,
           row_number() OVER (PARTITION BY r.idx ORDER BY ts_rank(s.tsv, websearch_to_tsquery('english', r.q)) DESC) AS fts_rank
    FROM rewrites r
    JOIN search_index s
      ON s.org_id = filter_org_id
     AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
    LIMIT 50
),
vec AS (
    SELECT r.idx, s.object_type, s.object_id,
           CASE WHEN r.v IS NULL THEN NULL ELSE 1 - (s.embedding <=> r.v) END AS vector_sim,
           CASE WHEN r.v IS NULL THEN NULL ELSE row_number() OVER (PARTITION BY r.idx ORDER BY s.embedding <=> r.v ASC) END AS vector_rank
    FROM rewrites r
    JOIN search_index s
      ON s.org_id = filter_org_id
     AND (filter_yacht_id IS NULL OR s.yacht_id = filter_yacht_id)
    WHERE s.embedding IS NOT NULL
    LIMIT 100
),
unioned AS (
    SELECT idx, object_type, object_id,
           MIN(trigram_rank) AS trigram_rank,
           MIN(fts_rank) AS fts_rank,
           MIN(vector_rank) AS vector_rank,
           MAX(trigram_score) AS trigram_score,
           MAX(fts_score) AS fts_score,
           MAX(vector_sim) AS vector_sim
    FROM (
        SELECT * FROM trigram
        UNION ALL SELECT * FROM fts
        UNION ALL SELECT * FROM vec
    ) u
    GROUP BY 1,2,3
)
SELECT u.object_type, u.object_id, COALESCE(s.payload, '{}'::jsonb) AS payload,
       (COALESCE(1.0/(rrf_k + u.trigram_rank),0) +
        COALESCE(1.0/(rrf_k + u.fts_rank),0) +
        COALESCE(1.0/(rrf_k + u.vector_rank),0)) AS fused_score,
       (array_agg(u.idx ORDER BY
           COALESCE(1.0/(rrf_k + u.trigram_rank),0) +
           COALESCE(1.0/(rrf_k + u.fts_rank),0) +
           COALESCE(1.0/(rrf_k + u.vector_rank),0) DESC))[1] AS best_rewrite_idx,
       jsonb_build_object('trigram', u.trigram_rank, 'fts', u.fts_rank, 'vector', u.vector_rank) AS ranks,
       jsonb_build_object('trigram', u.trigram_score, 'fts', u.fts_score, 'vector', u.vector_sim) AS components
FROM unioned u
LEFT JOIN search_index s
  ON s.object_type = u.object_type AND s.object_id = u.object_id
ORDER BY fused_score DESC
LIMIT page_limit;
$$;

ANALYZE search_index;
