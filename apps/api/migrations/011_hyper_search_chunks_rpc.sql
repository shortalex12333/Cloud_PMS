-- Migration 011: Chunk-Level Hybrid Search RPC
-- Purpose: Search chunks within specific documents for RAG grounding
--
-- Key fixes from original proposal:
-- 1. Uses correct column names: document_id, chunk_index, content/search_text
-- 2. Returns search_text (actual content) for LLM grounding
-- 3. Uses yacht_id for RLS filtering (not org_id which may not exist)
-- 4. Includes offset columns for PDF citation highlighting

-- Drop old version if exists (handles signature changes)
DROP FUNCTION IF EXISTS hyper_search_chunks_for_docs(text[], vector(1536)[], uuid[], uuid, uuid, int, int, int, float);

CREATE OR REPLACE FUNCTION hyper_search_chunks_for_docs(
    rewrite_texts       text[],
    rewrite_embeddings  vector(1536)[],
    doc_ids             uuid[],           -- Constrain to these documents from Stage 1
    filter_org_id       uuid,             -- For logging/future use (RLS uses yacht_id)
    filter_yacht_id     uuid,             -- Primary RLS filter
    rrf_k               int DEFAULT 60,
    page_limit          int DEFAULT 10,   -- Total chunks to return
    chunks_per_doc      int DEFAULT 3,    -- Max chunks per document
    trigram_limit       float DEFAULT 0.15
) RETURNS TABLE (
    object_type         text,
    object_id           uuid,             -- document_id
    chunk_id            int,              -- chunk_index
    search_text         text,             -- ACTUAL CONTENT for LLM grounding
    payload             jsonb,            -- metadata (heading, page, etc.)
    start_offset        int,
    end_offset          int,
    global_offset_start int,
    fused_score         double precision,
    ranks               jsonb,
    components          jsonb
) SECURITY INVOKER LANGUAGE plpgsql AS $$
BEGIN
    -- Set trigram threshold inline (single round-trip)
    PERFORM set_limit(trigram_limit);

    RETURN QUERY
    WITH rewrites AS (
        SELECT
            generate_subscripts(rewrite_texts, 1) AS idx,
            rewrite_texts[generate_subscripts(rewrite_texts, 1)] AS q,
            rewrite_embeddings[generate_subscripts(rewrite_embeddings, 1)] AS v
    ),
    -- Trigram matches (uses search_text column with gin_trgm_ops index)
    trigram AS (
        SELECT
            r.idx,
            c.document_id,
            c.chunk_index,
            similarity(c.search_text, r.q) AS trigram_score,
            row_number() OVER (PARTITION BY r.idx ORDER BY similarity(c.search_text, r.q) DESC) AS trigram_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.search_text IS NOT NULL
          AND c.search_text % r.q
        LIMIT 200
    ),
    -- FTS matches (uses tsv column with gin index)
    fts AS (
        SELECT
            r.idx,
            c.document_id,
            c.chunk_index,
            ts_rank(c.tsv, websearch_to_tsquery('english', r.q)) AS fts_score,
            row_number() OVER (PARTITION BY r.idx ORDER BY ts_rank(c.tsv, websearch_to_tsquery('english', r.q)) DESC) AS fts_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.tsv IS NOT NULL
          AND c.tsv @@ websearch_to_tsquery('english', r.q)
        LIMIT 200
    ),
    -- Vector matches (uses embedding column with hnsw index)
    vec AS (
        SELECT
            r.idx,
            c.document_id,
            c.chunk_index,
            CASE WHEN r.v IS NULL THEN NULL ELSE 1 - (c.embedding <=> r.v) END AS vector_sim,
            CASE WHEN r.v IS NULL THEN NULL
                 ELSE row_number() OVER (PARTITION BY r.idx ORDER BY c.embedding <=> r.v ASC)
            END AS vector_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.embedding IS NOT NULL
          AND r.v IS NOT NULL
        LIMIT 200
    ),
    -- Union all retrieval methods
    unioned AS (
        SELECT
            idx, document_id, chunk_index,
            MIN(trigram_rank) AS trigram_rank,
            MIN(fts_rank) AS fts_rank,
            MIN(vector_rank) AS vector_rank,
            MAX(trigram_score) AS trigram_score,
            MAX(fts_score) AS fts_score,
            MAX(vector_sim) AS vector_sim
        FROM (
            SELECT idx, document_id, chunk_index, trigram_rank,
                   NULL::bigint AS fts_rank, NULL::bigint AS vector_rank,
                   trigram_score, NULL::real AS fts_score, NULL::double precision AS vector_sim
            FROM trigram
            UNION ALL
            SELECT idx, document_id, chunk_index,
                   NULL, fts_rank, NULL,
                   NULL, fts_score, NULL
            FROM fts
            UNION ALL
            SELECT idx, document_id, chunk_index,
                   NULL, NULL, vector_rank,
                   NULL, NULL, vector_sim
            FROM vec
        ) combined
        GROUP BY idx, document_id, chunk_index
    ),
    -- RRF fusion scoring with per-document ranking
    scored AS (
        SELECT
            u.document_id,
            u.chunk_index,
            (COALESCE(1.0 / (rrf_k + u.trigram_rank), 0) +
             COALESCE(1.0 / (rrf_k + u.fts_rank), 0) +
             COALESCE(1.0 / (rrf_k + u.vector_rank), 0)) AS fused_score,
            jsonb_build_object(
                'trigram', u.trigram_rank,
                'fts', u.fts_rank,
                'vector', u.vector_rank
            ) AS ranks,
            jsonb_build_object(
                'trigram', u.trigram_score,
                'fts', u.fts_score,
                'vector', u.vector_sim
            ) AS components,
            row_number() OVER (
                PARTITION BY u.document_id
                ORDER BY (COALESCE(1.0 / (rrf_k + u.trigram_rank), 0) +
                          COALESCE(1.0 / (rrf_k + u.fts_rank), 0) +
                          COALESCE(1.0 / (rrf_k + u.vector_rank), 0)) DESC
            ) AS rn_doc
        FROM unioned u
    )
    -- Final select with actual content
    SELECT
        'document'::text AS object_type,
        c.document_id AS object_id,
        c.chunk_index AS chunk_id,
        COALESCE(c.content, c.search_text, '') AS search_text,  -- Return actual content!
        COALESCE(c.metadata, '{}'::jsonb) AS payload,
        COALESCE(c.start_offset, 0) AS start_offset,
        COALESCE(c.end_offset, LENGTH(COALESCE(c.content, ''))) AS end_offset,
        COALESCE(c.global_offset_start, 0) AS global_offset_start,
        s.fused_score,
        s.ranks,
        s.components
    FROM scored s
    JOIN search_document_chunks c
        ON c.document_id = s.document_id
        AND c.chunk_index = s.chunk_index
    WHERE s.rn_doc <= chunks_per_doc
    ORDER BY s.fused_score DESC
    LIMIT page_limit;
END;
$$;

-- Add comment for documentation
COMMENT ON FUNCTION hyper_search_chunks_for_docs IS
'Chunk-level hybrid search (trigram + FTS + vector) constrained to specific documents.
Returns actual content text for RAG grounding. Uses RRF fusion with per-document caps.
Key: Returns search_text with actual content, not just metadata.';

-- Analyze to update statistics
ANALYZE search_document_chunks;
