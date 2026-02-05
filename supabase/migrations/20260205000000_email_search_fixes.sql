-- =============================================================================
-- MIGRATION: Email Search Fixes (2026-02-05)
-- =============================================================================
-- PURPOSE: Fix critical issues in email search infrastructure
--
-- FIXES:
--   1. Column mismatch: search_email_hybrid reads from `embedding` but sync
--      writes to `meta_embedding` - update RPC to use meta_embedding
--   2. Missing operator filters: p_from, p_to, p_subject, p_has_attachment
--      not supported by RPC but passed by Python code
--   3. Missing M3 signals: recency, affinity, linkage scoring not implemented
--   4. Missing web_link column for "Open in Outlook" feature
--
-- IMPACT: Email search will now actually use vector embeddings (was broken)
-- =============================================================================

-- =============================================================================
-- PART 1: ADD web_link COLUMN FOR "OPEN IN OUTLOOK"
-- =============================================================================

ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS web_link TEXT;

COMMENT ON COLUMN public.email_messages.web_link IS
    'Microsoft Graph webLink URL - opens message in Outlook Web App. Fetched during sync.';

-- Index for quick lookup (null check is cheap)
CREATE INDEX IF NOT EXISTS idx_email_messages_has_web_link
    ON public.email_messages(id)
    WHERE web_link IS NOT NULL;

-- =============================================================================
-- PART 2: ADD from_address_hash INDEX (for affinity scoring)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_email_messages_from_hash
    ON public.email_messages(yacht_id, from_address_hash, sent_at DESC);

-- =============================================================================
-- PART 3: REPLACE search_email_hybrid WITH FIXED VERSION
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
            em.thread_id,
            em.subject,
            em.preview_text,
            em.from_display_name,
            em.from_address_hash,
            em.sent_at,
            em.direction,
            em.has_attachments,
            em.web_link,
            em.meta_embedding  -- Use meta_embedding, not embedding
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
            eer.message_id,
            COUNT(*) AS match_count,
            ARRAY_AGG(DISTINCT eer.entity_value) AS matched_values
        FROM public.email_extraction_results eer
        WHERE eer.yacht_id = p_yacht_id
          AND eer.entity_value = ANY(p_entity_keywords)
        GROUP BY eer.message_id
    ),

    -- Step 4: Affinity scoring (emails from same sender as user)
    affinity_data AS (
        SELECT DISTINCT from_address_hash
        FROM public.email_messages
        WHERE yacht_id = p_yacht_id
          AND from_address_hash = p_user_email_hash
          AND p_user_email_hash IS NOT NULL
    ),

    -- Step 5: Linkage scoring (threads with existing links)
    linked_threads AS (
        SELECT DISTINCT thread_id
        FROM public.email_links
        WHERE yacht_id = p_yacht_id
          AND is_active = TRUE
    ),

    -- Step 6: Compute all scores
    scored AS (
        SELECT
            vs.id,
            vs.thread_id,
            vs.subject,
            vs.preview_text,
            vs.from_display_name,
            vs.from_address_hash,
            vs.sent_at,
            vs.direction,
            vs.has_attachments,
            vs.web_link,
            -- Vector score (0-1)
            vs.v_score,
            -- Entity score (0-1)
            COALESCE(
                em.match_count::FLOAT / NULLIF(array_length(p_entity_keywords, 1), 0),
                0.0
            ) AS e_score,
            em.matched_values,
            -- Recency score: exponential decay over 90 days (0-1)
            CASE WHEN p_boost_recency THEN
                EXP(-0.02 * EXTRACT(EPOCH FROM (v_now - vs.sent_at)) / 86400.0)
            ELSE 0.0 END AS r_score,
            -- Affinity score: 1 if from user's frequently contacted, else 0
            CASE WHEN p_boost_affinity AND ad.from_address_hash IS NOT NULL
                THEN 0.3 ELSE 0.0 END AS a_score,
            -- Linkage score: 0.2 if thread already has links
            CASE WHEN p_boost_linkage AND lt.thread_id IS NOT NULL
                THEN 0.2 ELSE 0.0 END AS l_score
        FROM vector_scored vs
        LEFT JOIN entity_matches em ON em.message_id = vs.id
        LEFT JOIN affinity_data ad ON ad.from_address_hash = vs.from_address_hash
        LEFT JOIN linked_threads lt ON lt.thread_id = vs.thread_id
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
            ) AS total
        FROM scored s
    )

    SELECT
        fs.id AS message_id,
        fs.thread_id,
        fs.subject,
        fs.preview_text,
        fs.from_display_name,
        fs.from_address_hash,
        fs.sent_at,
        fs.direction,
        fs.has_attachments,
        fs.web_link,
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
    ORDER BY fs.total DESC, fs.sent_at DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.search_email_hybrid TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_email_hybrid TO service_role;

COMMENT ON FUNCTION public.search_email_hybrid IS
    'Hybrid email search: vector similarity (meta_embedding) + entity keywords + M3 signals (recency, affinity, linkage). Supports operator filters.';

-- =============================================================================
-- PART 4: VALIDATION
-- =============================================================================

DO $$
BEGIN
    -- Check web_link column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_messages' AND column_name = 'web_link'
    ) THEN
        RAISE EXCEPTION 'web_link column not added to email_messages';
    END IF;

    -- Check function exists and has correct signature
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
          AND p.proname = 'search_email_hybrid'
          AND pg_get_function_arguments(p.oid) LIKE '%p_from%'
    ) THEN
        RAISE EXCEPTION 'search_email_hybrid not updated with operator filters';
    END IF;

    RAISE NOTICE 'Migration: Email Search Fixes completed successfully';
    RAISE NOTICE '  - Added web_link column';
    RAISE NOTICE '  - Updated search_email_hybrid to use meta_embedding';
    RAISE NOTICE '  - Added operator filter support (from, to, subject, has_attachment)';
    RAISE NOTICE '  - Added M3 signal scoring (recency, affinity, linkage)';
END $$;
