-- Migration 26: Email Hybrid Search RPC
-- Creates the canonical hybrid search function for email RAG
--
-- IMPORTANT: This RPC uses email_messages.meta_embedding (VECTOR(1536))
-- The meta_embedding column is the CANONICAL embedding column for hybrid search.
-- It is populated by EmailEmbeddingService.backfill_embeddings().
-- The legacy 'embedding' column exists but is NOT used - do not write to it.
--
-- Dependencies:
--   - pgvector extension (for vector similarity)
--   - pg_trgm extension (for ILIKE optimization)
--   - email_messages table with meta_embedding column (VECTOR(1536))
--   - email_extraction_results table for entity matching

-- Ensure required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Canonical hybrid search RPC (vector + entities)
-- Scoring: 0.60 * vector_score + 0.25 * entity_score
-- Entity score capped at 0.5 pre-weight (max contribution 0.125)
CREATE OR REPLACE FUNCTION public.search_email_hybrid(
    p_yacht_id UUID,
    p_embedding VECTOR(1536),
    p_entity_keywords TEXT[] DEFAULT '{}',
    p_limit INT DEFAULT 20,
    p_similarity_threshold FLOAT8 DEFAULT 0.30,
    p_date_from TIMESTAMPTZ DEFAULT NULL,
    p_date_to TIMESTAMPTZ DEFAULT NULL,
    p_from_display_name TEXT DEFAULT NULL,
    p_has_attachment BOOLEAN DEFAULT NULL,
    p_direction TEXT DEFAULT NULL
)
RETURNS TABLE(
    message_id UUID,
    thread_id UUID,
    subject TEXT,
    preview_text TEXT,
    from_display_name TEXT,
    sent_at TIMESTAMPTZ,
    direction TEXT,
    has_attachments BOOLEAN,
    vector_score FLOAT8,
    entity_score FLOAT8,
    total_score FLOAT8,
    matched_entities TEXT[]
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
WITH base AS (
    SELECT
        m.id AS message_id,
        m.thread_id,
        m.subject,
        m.preview_text,
        m.from_display_name,
        m.sent_at,
        m.direction,
        m.has_attachments,
        CASE
            WHEN m.meta_embedding IS NULL THEN 0
            ELSE 1 - (m.meta_embedding <=> p_embedding) / 2.0  -- cosine_sim = 1 - dist/2
        END AS vector_score
    FROM public.email_messages m
    WHERE m.yacht_id = p_yacht_id
      AND m.is_active = TRUE
      AND (p_date_from IS NULL OR m.sent_at >= p_date_from)
      AND (p_date_to IS NULL OR m.sent_at <= p_date_to)
      AND (p_from_display_name IS NULL OR m.from_display_name ILIKE '%' || p_from_display_name || '%')
      AND (p_has_attachment IS NULL OR m.has_attachments = p_has_attachment)
      AND (p_direction IS NULL OR m.direction = p_direction)
),
kw AS (
    SELECT
        e.message_id,
        ARRAY_AGG(DISTINCT e.entity_value) AS matched_entities,
        COUNT(DISTINCT e.entity_value) AS matches
    FROM public.email_extraction_results e
    WHERE e.yacht_id = p_yacht_id
      AND array_length(p_entity_keywords, 1) IS NOT NULL
      AND e.entity_value ILIKE ANY (SELECT '%' || k || '%' FROM unnest(p_entity_keywords) AS k)
    GROUP BY e.message_id
),
scored AS (
    SELECT
        b.*,
        COALESCE(k.matches, 0) AS entity_matches,
        COALESCE(k.matched_entities, ARRAY[]::text[]) AS matched_entities,
        CASE
            WHEN array_length(p_entity_keywords, 1) IS NULL OR array_length(p_entity_keywords, 1) = 0 THEN 0
            ELSE LEAST(k.matches::float / array_length(p_entity_keywords, 1), 0.5)
        END AS entity_score
    FROM base b
    LEFT JOIN kw k ON k.message_id = b.message_id
)
SELECT
    s.message_id,
    s.thread_id,
    s.subject,
    s.preview_text,
    s.from_display_name,
    s.sent_at,
    s.direction,
    s.has_attachments,
    s.vector_score,
    s.entity_score,
    (0.60 * s.vector_score + 0.25 * s.entity_score) AS total_score,
    s.matched_entities
FROM scored s
WHERE s.vector_score >= p_similarity_threshold
   OR (array_length(p_entity_keywords, 1) > 0 AND s.entity_score > 0)
ORDER BY (0.60 * s.vector_score + 0.25 * s.entity_score) DESC, s.sent_at DESC, s.message_id
LIMIT p_limit;
$$;

-- Grant execute to backend role
GRANT EXECUTE ON FUNCTION public.search_email_hybrid(
    UUID, VECTOR(1536), TEXT[], INT, FLOAT8, TIMESTAMPTZ, TIMESTAMPTZ, TEXT, BOOLEAN, TEXT
) TO service_role;

-- Also grant to authenticated users for direct RPC calls
GRANT EXECUTE ON FUNCTION public.search_email_hybrid(
    UUID, VECTOR(1536), TEXT[], INT, FLOAT8, TIMESTAMPTZ, TIMESTAMPTZ, TEXT, BOOLEAN, TEXT
) TO authenticated;

COMMENT ON FUNCTION public.search_email_hybrid IS
'Hybrid email search combining vector similarity (60%) and entity matching (25%).
Vector score: cosine similarity from embedding column.
Entity score: keyword matches from email_extraction_results, capped at 0.5.
Returns results above similarity threshold OR with entity matches.';
