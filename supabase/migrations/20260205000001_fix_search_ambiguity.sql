-- =============================================================================
-- MIGRATION: Fix search_email_hybrid column ambiguity (2026-02-05)
-- =============================================================================
-- FIXES: PostgreSQL error 42702 "column reference is ambiguous"
-- The return columns (from_address_hash, thread_id) conflict with unqualified
-- column references in CTEs. Adding table aliases fixes the ambiguity.
-- =============================================================================

DROP FUNCTION IF EXISTS public.search_email_hybrid CASCADE;

CREATE OR REPLACE FUNCTION public.search_email_hybrid(
    -- Required params
    p_yacht_id UUID,
    p_embedding VECTOR(1536),
    -- Entity search
    p_entity_keywords TEXT[] DEFAULT '{}',
    -- Date filters
    p_date_from TIMESTAMPTZ DEFAULT NULL,
    p_date_to TIMESTAMPTZ DEFAULT NULL,
    -- Pagination
    p_limit INT DEFAULT 20,
    p_similarity_threshold FLOAT DEFAULT 0.3,
    -- Operator filters (from query_parser)
    p_from TEXT DEFAULT NULL,
    p_to TEXT DEFAULT NULL,
    p_subject TEXT DEFAULT NULL,
    p_has_attachment BOOLEAN DEFAULT NULL,
    p_direction TEXT DEFAULT NULL,
    -- M3 signal controls
    p_user_email_hash TEXT DEFAULT NULL,
    p_boost_recency BOOLEAN DEFAULT TRUE,
    p_boost_affinity BOOLEAN DEFAULT TRUE,
    p_boost_linkage BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    message_id UUID,
    thread_id UUID,
    subject TEXT,
    preview_text TEXT,
    from_display_name TEXT,
    from_address_hash TEXT,
    sent_at TIMESTAMPTZ,
    direction TEXT,
    has_attachments BOOLEAN,
    web_link TEXT,
    vector_score FLOAT,
    entity_score FLOAT,
    recency_score FLOAT,
    affinity_score FLOAT,
    linkage_score FLOAT,
    total_score FLOAT,
    matched_entities TEXT[],
    filters_applied TEXT[],
    score_breakdown JSONB
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_filters_applied TEXT[] := '{}';
    v_now TIMESTAMPTZ := NOW();
    v_embedding_is_zero BOOLEAN;
BEGIN
    -- Detect if embedding is zero vector (operator-only query)
    v_embedding_is_zero := (SELECT p_embedding = (ARRAY_FILL(0::float, ARRAY[1536]))::vector);

    -- Track which filters are active
    IF p_from IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'from'); END IF;
    IF p_to IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'to'); END IF;
    IF p_subject IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'subject'); END IF;
    IF p_has_attachment IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'has_attachment'); END IF;
    IF p_direction IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'direction'); END IF;
    IF p_date_from IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'after'); END IF;
    IF p_date_to IS NOT NULL THEN v_filters_applied := array_append(v_filters_applied, 'before'); END IF;

    RETURN QUERY
    WITH
    -- Step 1: Apply hard filters first (most selective)
    filtered_messages AS (
        SELECT
            em.id,
            em.thread_id AS msg_thread_id,
            em.subject AS msg_subject,
            em.preview_text AS msg_preview_text,
            em.from_display_name AS msg_from_display_name,
            em.from_address_hash AS msg_from_address_hash,
            em.sent_at AS msg_sent_at,
            em.direction AS msg_direction,
            em.has_attachments AS msg_has_attachments,
            em.web_link AS msg_web_link,
            em.meta_embedding
        FROM public.email_messages em
        WHERE em.yacht_id = p_yacht_id
          -- Date filters
          AND (p_date_from IS NULL OR em.sent_at >= p_date_from)
          AND (p_date_to IS NULL OR em.sent_at <= p_date_to)
          -- Operator filters
          AND (p_from IS NULL OR em.from_display_name ILIKE '%' || p_from || '%'
               OR em.from_address_hash = p_from)
          AND (p_to IS NULL OR em.to_addresses_hash @> ARRAY[p_to])
          AND (p_subject IS NULL OR em.subject ILIKE '%' || p_subject || '%')
          AND (p_has_attachment IS NULL OR em.has_attachments = p_has_attachment)
          AND (p_direction IS NULL OR em.direction = p_direction)
    ),

    -- Step 2: Vector similarity (only if embedding provided and not zero)
    vector_scored AS (
        SELECT
            fm.*,
            CASE
                WHEN v_embedding_is_zero OR fm.meta_embedding IS NULL THEN 0.0
                ELSE GREATEST(0, 1 - (fm.meta_embedding <=> p_embedding))
            END AS v_score
        FROM filtered_messages fm
    ),

    -- Step 3: Entity keyword matching
    entity_matches AS (
        SELECT
            eer.message_id AS eer_message_id,
            COUNT(*) AS match_count,
            ARRAY_AGG(DISTINCT eer.entity_value) AS matched_values
        FROM public.email_extraction_results eer
        WHERE eer.yacht_id = p_yacht_id
          AND eer.entity_value = ANY(p_entity_keywords)
        GROUP BY eer.message_id
    ),

    -- Step 4: Affinity scoring (emails from same sender as user)
    -- FIX: Use table alias to avoid ambiguity with return column from_address_hash
    affinity_data AS (
        SELECT DISTINCT aem.from_address_hash AS affinity_hash
        FROM public.email_messages aem
        WHERE aem.yacht_id = p_yacht_id
          AND aem.from_address_hash = p_user_email_hash
          AND p_user_email_hash IS NOT NULL
    ),

    -- Step 5: Linkage scoring (threads with existing links)
    -- FIX: Use table alias to avoid ambiguity with return column thread_id
    linked_threads AS (
        SELECT DISTINCT el.thread_id AS linked_thread_id
        FROM public.email_links el
        WHERE el.yacht_id = p_yacht_id
          AND el.is_active = TRUE
    ),

    -- Step 6: Compute all scores
    scored AS (
        SELECT
            vs.id,
            vs.msg_thread_id,
            vs.msg_subject,
            vs.msg_preview_text,
            vs.msg_from_display_name,
            vs.msg_from_address_hash,
            vs.msg_sent_at,
            vs.msg_direction,
            vs.msg_has_attachments,
            vs.msg_web_link,
            -- Vector score (0-1)
            vs.v_score,
            -- Entity score (0-1)
            COALESCE(
                em.match_count::FLOAT / NULLIF(array_length(p_entity_keywords, 1), 0),
                0.0::FLOAT
            )::FLOAT AS e_score,
            em.matched_values,
            -- Recency score: exponential decay over 90 days (0-1)
            (CASE WHEN p_boost_recency THEN
                EXP(-0.02 * EXTRACT(EPOCH FROM (v_now - vs.msg_sent_at)) / 86400.0)
            ELSE 0.0 END)::FLOAT AS r_score,
            -- Affinity score: 0.3 if from user's frequently contacted, else 0
            (CASE WHEN p_boost_affinity AND ad.affinity_hash IS NOT NULL
                THEN 0.3 ELSE 0.0 END)::FLOAT AS a_score,
            -- Linkage score: 0.2 if thread already has links
            (CASE WHEN p_boost_linkage AND lt.linked_thread_id IS NOT NULL
                THEN 0.2 ELSE 0.0 END)::FLOAT AS l_score
        FROM vector_scored vs
        LEFT JOIN entity_matches em ON em.eer_message_id = vs.id
        LEFT JOIN affinity_data ad ON ad.affinity_hash = vs.msg_from_address_hash
        LEFT JOIN linked_threads lt ON lt.linked_thread_id = vs.msg_thread_id
        -- Apply similarity threshold (skip if zero embedding)
        WHERE v_embedding_is_zero
           OR vs.v_score > p_similarity_threshold
           OR em.match_count > 0
    ),

    -- Step 7: Compute total score with weights
    -- Weights: 60% vector, 25% entity, 10% recency, 3% affinity, 2% linkage
    final_scored AS (
        SELECT
            s.*,
            (
                s.v_score * 0.60 +
                s.e_score * 0.25 +
                s.r_score * 0.10 +
                s.a_score * 0.03 +
                s.l_score * 0.02
            )::FLOAT AS total
        FROM scored s
    )

    SELECT
        fs.id AS message_id,
        fs.msg_thread_id AS thread_id,
        fs.msg_subject AS subject,
        fs.msg_preview_text AS preview_text,
        fs.msg_from_display_name AS from_display_name,
        fs.msg_from_address_hash AS from_address_hash,
        fs.msg_sent_at AS sent_at,
        fs.msg_direction AS direction,
        fs.msg_has_attachments AS has_attachments,
        fs.msg_web_link AS web_link,
        fs.v_score AS vector_score,
        fs.e_score AS entity_score,
        fs.r_score AS recency_score,
        fs.a_score AS affinity_score,
        fs.l_score AS linkage_score,
        fs.total AS total_score,
        fs.matched_values AS matched_entities,
        v_filters_applied AS filters_applied,
        jsonb_build_object(
            'vector', fs.v_score,
            'entity', fs.e_score,
            'recency', fs.r_score,
            'affinity', fs.a_score,
            'linkage', fs.l_score,
            'weights', jsonb_build_object(
                'vector', 0.60,
                'entity', 0.25,
                'recency', 0.10,
                'affinity', 0.03,
                'linkage', 0.02
            )
        ) AS score_breakdown
    FROM final_scored fs
    ORDER BY fs.total DESC, fs.msg_sent_at DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.search_email_hybrid TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_email_hybrid TO service_role;

COMMENT ON FUNCTION public.search_email_hybrid IS
    'Hybrid email search: vector similarity (meta_embedding) + entity keywords + M3 signals (recency, affinity, linkage). Supports operator filters. Fixed column ambiguity.';

-- Validation
DO $$
BEGIN
    -- Quick test - should not error
    PERFORM 1 FROM search_email_hybrid(
        p_yacht_id := '00000000-0000-0000-0000-000000000000'::uuid,
        p_embedding := (ARRAY_FILL(0::float, ARRAY[1536]))::vector,
        p_limit := 1
    );
    RAISE NOTICE 'Migration: search_email_hybrid ambiguity fix completed successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'search_email_hybrid test failed: %', SQLERRM;
END $$;
