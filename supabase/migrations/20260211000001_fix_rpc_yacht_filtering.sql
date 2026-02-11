-- Migration: Fix RPC yacht_id filtering
-- Purpose: Security fix - SECURITY DEFINER functions must filter by yacht_id
--          to prevent cross-yacht data exposure.
--
-- CRITICAL: These functions bypass RLS. Without yacht_id filtering, they return
--           ALL threads across ALL yachts, causing security issues.

-- =============================================================================
-- FIX: get_stale_link_threads
-- =============================================================================
-- Now requires p_yacht_id parameter to scope results to a single yacht.
-- =============================================================================

DROP FUNCTION IF EXISTS public.get_stale_link_threads(TIMESTAMPTZ, INTEGER);

CREATE OR REPLACE FUNCTION public.get_stale_link_threads(
    p_yacht_id UUID,
    p_cutoff TIMESTAMPTZ,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    yacht_id UUID,
    latest_subject TEXT,
    extracted_tokens JSONB,
    participant_hashes TEXT[],
    suggestions_generated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        t.id,
        t.yacht_id,
        t.latest_subject,
        t.extracted_tokens,
        t.participant_hashes,
        t.suggestions_generated_at,
        t.updated_at
    FROM public.email_threads t
    WHERE
        -- SECURITY: Filter by yacht_id FIRST
        t.yacht_id = p_yacht_id
        -- Has been processed before
        AND t.suggestions_generated_at IS NOT NULL
        -- But has been updated since
        AND t.updated_at > t.suggestions_generated_at
        -- Within lookback window
        AND t.created_at >= p_cutoff
    ORDER BY t.updated_at DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION public.get_stale_link_threads IS
'Find threads updated since their last linking attempt. SECURITY: Requires yacht_id parameter.';


-- =============================================================================
-- FIX: get_unlinked_threads_with_tokens
-- =============================================================================
-- Now requires p_yacht_id parameter to scope results to a single yacht.
-- =============================================================================

DROP FUNCTION IF EXISTS public.get_unlinked_threads_with_tokens(TIMESTAMPTZ, INTEGER);

CREATE OR REPLACE FUNCTION public.get_unlinked_threads_with_tokens(
    p_yacht_id UUID,
    p_cutoff TIMESTAMPTZ,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    yacht_id UUID,
    latest_subject TEXT,
    extracted_tokens JSONB,
    participant_hashes TEXT[],
    created_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        t.id,
        t.yacht_id,
        t.latest_subject,
        t.extracted_tokens,
        t.participant_hashes,
        t.created_at
    FROM public.email_threads t
    WHERE
        -- SECURITY: Filter by yacht_id FIRST
        t.yacht_id = p_yacht_id
        -- Has tokens extracted
        AND t.extracted_tokens IS NOT NULL
        -- Has been processed
        AND t.suggestions_generated_at IS NOT NULL
        -- Within lookback window
        AND t.created_at >= p_cutoff
        -- But has no links
        AND NOT EXISTS (
            SELECT 1 FROM public.email_links el
            WHERE el.thread_id = t.id
        )
    ORDER BY t.created_at DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION public.get_unlinked_threads_with_tokens IS
'Find threads with tokens but no links. SECURITY: Requires yacht_id parameter.';


-- =============================================================================
-- ADD: email_linking_coverage_by_yacht function
-- =============================================================================
-- Replaces the global view with a yacht-scoped function.
-- =============================================================================

DROP VIEW IF EXISTS public.email_linking_coverage;

CREATE OR REPLACE FUNCTION public.get_email_linking_coverage(p_yacht_id UUID)
RETURNS TABLE (
    total_threads BIGINT,
    processed_threads BIGINT,
    linked_threads BIGINT,
    primary_links BIGINT,
    unlinked_with_tokens BIGINT,
    stale_threads BIGINT,
    linking_rate_pct NUMERIC
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        (SELECT COUNT(*) FROM public.email_threads WHERE yacht_id = p_yacht_id) AS total_threads,
        (SELECT COUNT(*) FROM public.email_threads WHERE yacht_id = p_yacht_id AND suggestions_generated_at IS NOT NULL) AS processed_threads,
        (SELECT COUNT(DISTINCT el.thread_id) FROM public.email_links el
         INNER JOIN public.email_threads t ON el.thread_id = t.id
         WHERE t.yacht_id = p_yacht_id) AS linked_threads,
        (SELECT COUNT(*) FROM public.email_links el
         INNER JOIN public.email_threads t ON el.thread_id = t.id
         WHERE t.yacht_id = p_yacht_id AND el.is_primary = true) AS primary_links,
        (SELECT COUNT(*) FROM public.email_threads t
         WHERE t.yacht_id = p_yacht_id
           AND t.extracted_tokens IS NOT NULL
           AND t.suggestions_generated_at IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM public.email_links WHERE thread_id = t.id)
        ) AS unlinked_with_tokens,
        (SELECT COUNT(*) FROM public.email_threads t
         WHERE t.yacht_id = p_yacht_id
           AND t.updated_at > t.suggestions_generated_at
        ) AS stale_threads,
        ROUND(
            100.0 * (
                SELECT COUNT(DISTINCT el.thread_id) FROM public.email_links el
                INNER JOIN public.email_threads t ON el.thread_id = t.id
                WHERE t.yacht_id = p_yacht_id
            ) /
            NULLIF((SELECT COUNT(*) FROM public.email_threads WHERE yacht_id = p_yacht_id), 0),
            1
        ) AS linking_rate_pct;
$$;

COMMENT ON FUNCTION public.get_email_linking_coverage IS
'Dashboard function for email linking pipeline health. SECURITY: Requires yacht_id parameter.';
