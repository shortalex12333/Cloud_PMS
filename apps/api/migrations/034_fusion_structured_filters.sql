-- Migration 034: Add Structured Filters to f1_search_fusion
-- ==============================================================
--
-- Adds p_filters jsonb parameter to enable structured filtering:
--   - status: Filter by payload->>'status' (draft, accepted, rejected, in_progress, etc.)
--   - compliance_state: Filter by payload->>'compliance_state' (compliant, violation)
--   - item_contains: Filter by search_text ILIKE '%value%' (for line-item content)
--   - vendor_name: Filter by payload->>'vendor_name'
--   - crew_name: Filter by payload->>'crew_name'
--
-- This addresses:
-- - "What receiving records are in draft status" -> p_filters = {"status": "draft"}
-- - "engineer rest hours violations" -> p_filters = {"compliance_state": "violation"}
-- - "deliveries with fuel filter elements" -> p_filters = {"item_contains": "fuel filter"}
--
-- Filters are applied in ALL candidate CTEs to ensure proper filtering.

DROP FUNCTION IF EXISTS public.f1_search_fusion;

CREATE OR REPLACE FUNCTION public.f1_search_fusion(
    p_yacht_id uuid,
    p_query_text text,
    p_query_embedding vector(1536) DEFAULT NULL,
    p_role text DEFAULT 'default',
    p_lens text DEFAULT 'default',
    -- Domain/mode parameters
    p_domain text DEFAULT NULL,
    p_mode text DEFAULT 'explore',
    p_domain_boost numeric DEFAULT 0.25,
    -- Weight parameters
    p_w_text numeric DEFAULT 0.40,
    p_w_vector numeric DEFAULT 0.25,
    p_w_recency numeric DEFAULT 0.10,
    p_w_bias numeric DEFAULT 0.10,
    p_w_rrf numeric DEFAULT 0.15,
    p_lambda numeric DEFAULT 0.01,
    p_rrf_k integer DEFAULT 60,
    p_logistic_a numeric DEFAULT 6.0,
    p_logistic_b numeric DEFAULT 0.2,
    p_m_text integer DEFAULT 200,
    p_m_vec integer DEFAULT 200,
    p_limit integer DEFAULT 20,
    p_offset integer DEFAULT 0,
    p_debug boolean DEFAULT false,
    -- Trigram parameters
    p_trgm_limit real DEFAULT 0.15,
    p_m_trgm integer DEFAULT 100,
    p_w_trigram numeric DEFAULT 0.15,
    -- NEW: Structured filters
    p_filters jsonb DEFAULT NULL
)
RETURNS TABLE(
    object_id uuid,
    object_type text,
    payload jsonb,
    final_score numeric,
    s_text numeric,
    s_vector numeric,
    s_recency numeric,
    s_bias numeric,
    s_domain numeric,
    rank_text bigint,
    rank_vector bigint,
    score numeric,
    rrf_score numeric
)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_domain_types text[];
    v_status text;
    v_compliance_state text;
    v_item_contains text;
    v_vendor_name text;
    v_crew_name text;
BEGIN
    -- Set trigram threshold for this query
    PERFORM set_limit(p_trgm_limit);

    -- Extract filter values
    v_status := p_filters->>'status';
    v_compliance_state := p_filters->>'compliance_state';
    v_item_contains := p_filters->>'item_contains';
    v_vendor_name := p_filters->>'vendor_name';
    v_crew_name := p_filters->>'crew_name';

    -- Map domain to matching object types
    v_domain_types := CASE p_domain
        WHEN 'hours_of_rest' THEN ARRAY['hours_of_rest']
        WHEN 'inventory' THEN ARRAY['inventory', 'part', 'receiving']
        WHEN 'parts' THEN ARRAY['part', 'inventory']
        WHEN 'part' THEN ARRAY['part', 'inventory']
        WHEN 'equipment' THEN ARRAY['equipment']
        WHEN 'work_order' THEN ARRAY['work_order', 'work_order_note']
        WHEN 'fault' THEN ARRAY['fault']
        WHEN 'document' THEN ARRAY['document']
        WHEN 'certificate' THEN ARRAY['certificate']
        WHEN 'handover' THEN ARRAY['handover', 'handover_item']
        WHEN 'purchase' THEN ARRAY['purchase_order', 'shopping_item']
        WHEN 'shopping_list' THEN ARRAY['shopping_item']
        WHEN 'checklist' THEN ARRAY['checklist']
        WHEN 'crew' THEN ARRAY['crew', 'crew_member']
        WHEN 'receiving' THEN ARRAY['receiving']
        ELSE ARRAY[]::text[]
    END;

    RETURN QUERY
    WITH
    -- Text search candidates (Full-Text Search via tsvector)
    text_hits AS (
        SELECT
            si.object_id AS hit_id,
            ts_rank(COALESCE(si.tsv_generated, si.tsv), websearch_to_tsquery('english', p_query_text)) AS t_rank
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND COALESCE(si.tsv_generated, si.tsv) @@ websearch_to_tsquery('english', p_query_text)
          AND (p_mode != 'focused' OR p_domain IS NULL OR si.object_type = ANY(v_domain_types))
          -- Apply structured filters
          AND (v_status IS NULL OR si.payload->>'status' = v_status)
          AND (v_compliance_state IS NULL OR si.payload->>'compliance_state' = v_compliance_state)
          AND (v_item_contains IS NULL OR si.search_text ILIKE '%' || v_item_contains || '%')
          AND (v_vendor_name IS NULL OR si.payload->>'vendor_name' ILIKE '%' || v_vendor_name || '%')
          AND (v_crew_name IS NULL OR si.payload->>'crew_name' ILIKE '%' || v_crew_name || '%')
        ORDER BY t_rank DESC
        LIMIT p_m_text
    ),

    -- Trigram fuzzy matching (handles typos, partial matches)
    trigram_hits AS (
        SELECT
            si.object_id AS hit_id,
            similarity(si.search_text, p_query_text) AS trgm_score
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND si.search_text % p_query_text
          AND (p_mode != 'focused' OR p_domain IS NULL OR si.object_type = ANY(v_domain_types))
          -- Apply structured filters
          AND (v_status IS NULL OR si.payload->>'status' = v_status)
          AND (v_compliance_state IS NULL OR si.payload->>'compliance_state' = v_compliance_state)
          AND (v_item_contains IS NULL OR si.search_text ILIKE '%' || v_item_contains || '%')
          AND (v_vendor_name IS NULL OR si.payload->>'vendor_name' ILIKE '%' || v_vendor_name || '%')
          AND (v_crew_name IS NULL OR si.payload->>'crew_name' ILIKE '%' || v_crew_name || '%')
        ORDER BY trgm_score DESC
        LIMIT p_m_trgm
    ),

    -- Vector search candidates
    vec_hits AS (
        SELECT
            si.object_id AS hit_id,
            (1 - (si.embedding_1536 <=> p_query_embedding))::numeric AS v_sim
        FROM search_index si
        WHERE si.yacht_id = p_yacht_id
          AND si.embedding_1536 IS NOT NULL
          AND p_query_embedding IS NOT NULL
          AND (p_mode != 'focused' OR p_domain IS NULL OR si.object_type = ANY(v_domain_types))
          -- Apply structured filters
          AND (v_status IS NULL OR si.payload->>'status' = v_status)
          AND (v_compliance_state IS NULL OR si.payload->>'compliance_state' = v_compliance_state)
          AND (v_item_contains IS NULL OR si.search_text ILIKE '%' || v_item_contains || '%')
          AND (v_vendor_name IS NULL OR si.payload->>'vendor_name' ILIKE '%' || v_vendor_name || '%')
          AND (v_crew_name IS NULL OR si.payload->>'crew_name' ILIKE '%' || v_crew_name || '%')
        ORDER BY si.embedding_1536 <=> p_query_embedding ASC
        LIMIT p_m_vec
    ),

    -- Union all candidate sources
    candidates AS (
        SELECT DISTINCT hit_id AS cand_id FROM (
            SELECT hit_id FROM text_hits
            UNION ALL
            SELECT hit_id FROM trigram_hits
            UNION ALL
            SELECT hit_id FROM vec_hits
        ) u
    ),

    -- Compute features for each candidate
    features AS (
        SELECT
            si.object_id AS feat_id,
            si.object_type AS feat_type,
            si.payload AS feat_payload,
            si.updated_at AS feat_updated,
            th.t_rank AS feat_trank,
            tgh.trgm_score AS feat_trgm,
            vh.v_sim AS feat_vsim,

            -- S_text: normalized text rank (0-1)
            GREATEST(0, LEAST(1,
                COALESCE(th.t_rank, 0) / NULLIF(MAX(th.t_rank) OVER (), 0)
            ))::numeric AS s_text_raw,

            -- S_trigram: already 0-1 from similarity()
            COALESCE(tgh.trgm_score, 0)::numeric AS s_trigram_raw,

            -- S_vector: logistic-normalized cosine similarity (0-1)
            (1.0 / (1.0 + EXP(-p_logistic_a * (COALESCE(vh.v_sim, 0) - p_logistic_b))))::numeric AS s_vector_raw,

            -- S_recency: exponential decay (0-1)
            EXP(-p_lambda * GREATEST(0, EXTRACT(EPOCH FROM (NOW() - COALESCE(si.updated_at, NOW() - INTERVAL '1 year'))) / 86400.0))::numeric AS s_recency_raw,

            -- S_bias (role): from search_role_bias table (bounded ±0.2)
            GREATEST(-0.2, LEAST(0.2, COALESCE(bias.bias, 0.0)))::numeric AS s_role_bias,

            -- S_domain: boost if object_type matches detected domain
            CASE
                WHEN p_domain IS NOT NULL AND si.object_type = ANY(v_domain_types)
                THEN LEAST(p_domain_boost, 0.3)
                ELSE 0.0
            END::numeric AS s_domain_raw,

            -- Ranks for RRF (include trigram rank)
            RANK() OVER (ORDER BY COALESCE(th.t_rank, 0) DESC) AS r_text,
            RANK() OVER (ORDER BY COALESCE(tgh.trgm_score, 0) DESC) AS r_trigram,
            RANK() OVER (ORDER BY COALESCE(vh.v_sim, 0) DESC) AS r_vector

        FROM search_index si
        JOIN candidates c ON c.cand_id = si.object_id
        LEFT JOIN text_hits th ON th.hit_id = si.object_id
        LEFT JOIN trigram_hits tgh ON tgh.hit_id = si.object_id
        LEFT JOIN vec_hits vh ON vh.hit_id = si.object_id
        LEFT JOIN search_role_bias bias
            ON bias.role = p_role
            AND bias.lens = COALESCE(si.object_type, p_lens)
            AND (bias.doc_type IS NULL OR bias.doc_type = si.payload->>'doc_type')
            AND (bias.part_type IS NULL OR bias.part_type = si.payload->>'part_type')
        WHERE si.yacht_id = p_yacht_id
    ),

    -- Compute final scores
    scored AS (
        SELECT
            f.feat_id,
            f.feat_type,
            f.feat_payload,
            -- Use MAX of text and trigram for text score (best text match wins)
            GREATEST(f.s_text_raw, f.s_trigram_raw) AS s_text_combined,
            f.s_trigram_raw,
            f.s_vector_raw,
            f.s_recency_raw,
            GREATEST(-0.3, LEAST(0.3, f.s_role_bias + f.s_domain_raw))::numeric AS s_bias_combined,
            f.s_domain_raw,
            f.r_text,
            f.r_trigram,
            f.r_vector,

            -- RRF contribution (include trigram rank)
            (
                (1.0 / (p_rrf_k + f.r_text)) +
                (1.0 / (p_rrf_k + f.r_trigram)) +
                (1.0 / (p_rrf_k + f.r_vector))
            )::numeric AS rrf_contrib,

            -- Final score with trigram
            (
                p_w_text * GREATEST(f.s_text_raw, f.s_trigram_raw) +
                p_w_trigram * f.s_trigram_raw +
                p_w_vector * f.s_vector_raw +
                p_w_recency * f.s_recency_raw +
                p_w_bias * GREATEST(-0.3, LEAST(0.3, f.s_role_bias + f.s_domain_raw)) +
                p_w_rrf * (
                    (1.0 / (p_rrf_k + f.r_text)) +
                    (1.0 / (p_rrf_k + f.r_trigram)) +
                    (1.0 / (p_rrf_k + f.r_vector))
                )
            )::numeric AS final_score_calc

        FROM features f
    )

    -- Return results ordered by final score
    SELECT
        s.feat_id,
        s.feat_type,
        s.feat_payload,
        s.final_score_calc,
        CASE WHEN p_debug THEN s.s_text_combined ELSE NULL END,
        CASE WHEN p_debug THEN s.s_vector_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.s_recency_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.s_bias_combined ELSE NULL END,
        CASE WHEN p_debug THEN s.s_domain_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.r_text ELSE NULL END,
        CASE WHEN p_debug THEN s.r_vector ELSE NULL END,
        CASE WHEN p_debug THEN s.s_text_combined + s.s_vector_raw ELSE NULL END,
        CASE WHEN p_debug THEN s.rrf_contrib ELSE NULL END
    FROM scored s
    ORDER BY
        s.final_score_calc DESC,
        s.feat_type ASC,
        s.feat_id ASC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

COMMENT ON FUNCTION public.f1_search_fusion IS 'Hybrid search with FTS + Trigram + Vector + RRF fusion + Structured filters. Migration 034 adds p_filters jsonb for status/compliance/item filtering.';
