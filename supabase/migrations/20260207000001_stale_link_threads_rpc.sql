-- Migration: Add RPC to find threads needing re-linking
-- Purpose: Support the linking_requeue_worker by finding threads
--          where updated_at > suggestions_generated_at (new activity since last link)

-- =============================================================================
-- RPC: get_stale_link_threads
-- =============================================================================
-- Finds threads that have been updated since their last linking attempt.
-- This captures:
--   - New replies to a thread
--   - Subject line changes
--   - New attachments
--   - Any other metadata updates
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_stale_link_threads(
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
        -- Has been processed before
        t.suggestions_generated_at IS NOT NULL
        -- But has been updated since
        AND t.updated_at > t.suggestions_generated_at
        -- Within lookback window
        AND t.created_at >= p_cutoff
    ORDER BY t.updated_at DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION public.get_stale_link_threads IS
'Find threads updated since their last linking attempt. Used by linking_requeue_worker.';


-- =============================================================================
-- RPC: get_unlinked_threads_with_tokens
-- =============================================================================
-- Finds threads that have extracted_tokens but no email_links.
-- Useful for one-time backfills and monitoring.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_unlinked_threads_with_tokens(
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
        -- Has tokens extracted
        t.extracted_tokens IS NOT NULL
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
'Find threads with tokens but no links. Used for backfill and monitoring.';


-- =============================================================================
-- Monitoring View: email_linking_coverage
-- =============================================================================
-- Provides quick visibility into linking pipeline health.
-- =============================================================================

CREATE OR REPLACE VIEW public.email_linking_coverage AS
SELECT
    (SELECT COUNT(*) FROM public.email_threads) AS total_threads,
    (SELECT COUNT(*) FROM public.email_threads WHERE suggestions_generated_at IS NOT NULL) AS processed_threads,
    (SELECT COUNT(DISTINCT thread_id) FROM public.email_links) AS linked_threads,
    (SELECT COUNT(*) FROM public.email_links WHERE is_primary = true) AS primary_links,
    (SELECT COUNT(*) FROM public.email_threads
     WHERE extracted_tokens IS NOT NULL
       AND suggestions_generated_at IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM public.email_links WHERE thread_id = email_threads.id)
    ) AS unlinked_with_tokens,
    (SELECT COUNT(*) FROM public.email_threads
     WHERE updated_at > suggestions_generated_at
    ) AS stale_threads,
    ROUND(
        100.0 * (SELECT COUNT(DISTINCT thread_id) FROM public.email_links) /
        NULLIF((SELECT COUNT(*) FROM public.email_threads), 0),
        1
    ) AS linking_rate_pct;

COMMENT ON VIEW public.email_linking_coverage IS
'Dashboard view for email linking pipeline health and coverage metrics.';
