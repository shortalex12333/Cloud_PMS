-- ============================================================================
-- Migration 42: Counterfactual Feedback Loop (Tenant-Isolated Self-Healing Search)
-- ============================================================================
--
-- PURPOSE:
-- Implements a strictly tenant-isolated machine learning loop where search clicks
-- teach the system yacht-specific vocabulary WITHOUT cross-tenant pollution.
--
-- LAWS ENFORCED:
-- LAW 8: STRICT LINGUISTIC ISOLATION
--   All click aggregation and keyword learning is partitioned by yacht_id.
--   Yacht A's "watermaker" → Desalinator mapping will NEVER bleed into Yacht B.
--
-- LAW 9: PROJECTION IMMUTABILITY (No Overwrite Loops)
--   Worker 4 (Projectionist) overwrites search_text on CDC updates.
--   We introduce `learned_keywords` column that Worker 4 PRESERVES.
--   The tsv generated column concatenates both sources.
--
-- ============================================================================

-- ============================================================================
-- PART 1: Click Telemetry Table
-- ============================================================================
-- Records every search result click with full tenant context.
-- The nightly aggregator queries this table to learn vocabulary bridges.

CREATE TABLE IF NOT EXISTS public.search_click_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation (LAW 8)
    yacht_id UUID NOT NULL,
    org_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Search context
    search_id UUID NOT NULL,                    -- Correlates to the search session
    query_text TEXT NOT NULL,                   -- The exact query the user typed

    -- Clicked target
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,

    -- Result ranking context (for learning signal strength)
    result_rank INTEGER,                        -- Position in result list (1-indexed)
    fused_score NUMERIC(5,4),                   -- RRF score at time of click

    -- Temporal
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate clicks within same session
    CONSTRAINT unique_click_per_session
        UNIQUE (search_id, object_type, object_id)
);

-- Index for nightly aggregation: GROUP BY (yacht_id, object_id, query_text)
-- This is the hot path for the feedback loop
CREATE INDEX idx_click_events_aggregation
    ON public.search_click_events (yacht_id, object_id, query_text);

-- Index for time-bounded cleanup (delete clicks older than 90 days)
CREATE INDEX idx_click_events_clicked_at
    ON public.search_click_events (clicked_at);

-- Index for user analytics (optional dashboard queries)
CREATE INDEX idx_click_events_user
    ON public.search_click_events (yacht_id, user_id, clicked_at DESC);

-- RLS: Users can only insert clicks for their own yacht
ALTER TABLE public.search_click_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY click_events_insert_own_yacht ON public.search_click_events
    FOR INSERT
    WITH CHECK (
        yacht_id = (current_setting('request.jwt.claims', true)::json->>'yacht_id')::uuid
    );

-- Service role can read all for nightly aggregation
CREATE POLICY click_events_service_read ON public.search_click_events
    FOR SELECT
    USING (
        current_setting('role') = 'service_role'
        OR current_setting('role') = 'postgres'
    );

COMMENT ON TABLE public.search_click_events IS
    'Click telemetry for counterfactual learning. Strictly partitioned by yacht_id (LAW 8).';

-- ============================================================================
-- PART 2: Learned Keywords Column (Projection-Safe)
-- ============================================================================
-- Worker 4 MUST NOT touch this column. It is owned by the nightly feedback loop.
-- The tsv generated column will be updated to include learned_keywords.

-- Step 1: Add the learned_keywords column
ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS learned_keywords TEXT DEFAULT '';

-- Step 2: Add yacht-scoped learning metadata
ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS learned_at TIMESTAMPTZ;

-- Step 3: Recreate the tsv generated column to include learned_keywords
-- We must drop the existing generated column first, then recreate it.
-- This is safe because tsv is always regenerated from search_text.

-- Drop the existing generated column
ALTER TABLE public.search_index DROP COLUMN IF EXISTS tsv;

-- Recreate with learned_keywords included
ALTER TABLE public.search_index
    ADD COLUMN tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            COALESCE(search_text, '') || ' ' || COALESCE(learned_keywords, '')
        )
    ) STORED;

-- Recreate the GIN index on the new tsv column
DROP INDEX IF EXISTS idx_search_index_tsv;
CREATE INDEX idx_search_index_tsv
    ON public.search_index USING GIN (tsv);

COMMENT ON COLUMN public.search_index.learned_keywords IS
    'Yacht-specific vocabulary learned from click telemetry. NEVER overwrite from projection worker (LAW 9).';

COMMENT ON COLUMN public.search_index.learned_at IS
    'Timestamp of last learned_keywords update from nightly aggregator.';

-- ============================================================================
-- PART 3: Aggregated Learning Table (Optional: for audit trail)
-- ============================================================================
-- Stores the aggregated click counts per (yacht_id, object_id, query_text).
-- This provides an audit trail of what the system has learned.

CREATE TABLE IF NOT EXISTS public.search_learned_bridges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation (LAW 8)
    yacht_id UUID NOT NULL,

    -- Target object
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,

    -- Learned vocabulary
    query_text TEXT NOT NULL,                   -- The query that was clicked
    click_count INTEGER NOT NULL DEFAULT 1,     -- How many times this bridge was clicked

    -- Learning state
    applied BOOLEAN NOT NULL DEFAULT FALSE,     -- Has this been applied to search_index?
    applied_at TIMESTAMPTZ,

    -- Temporal
    first_clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique per (yacht, object, query)
    CONSTRAINT unique_learned_bridge
        UNIQUE (yacht_id, object_type, object_id, query_text)
);

-- Index for nightly application: find unapplied bridges above threshold
CREATE INDEX idx_learned_bridges_pending
    ON public.search_learned_bridges (yacht_id, applied, click_count DESC)
    WHERE NOT applied;

COMMENT ON TABLE public.search_learned_bridges IS
    'Audit trail of learned vocabulary bridges. Aggregated from search_click_events.';

-- ============================================================================
-- PART 4: Helper Function for Nightly Aggregation
-- ============================================================================
-- Aggregates clicks into learned_bridges, respecting tenant boundaries.

CREATE OR REPLACE FUNCTION public.aggregate_click_events(
    p_min_clicks INTEGER DEFAULT 3,
    p_lookback_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    yacht_id UUID,
    object_type TEXT,
    object_id UUID,
    query_text TEXT,
    click_count BIGINT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        sce.yacht_id,
        sce.object_type,
        sce.object_id,
        LOWER(TRIM(sce.query_text)) as query_text,
        COUNT(*) as click_count
    FROM public.search_click_events sce
    WHERE sce.clicked_at > NOW() - (p_lookback_days || ' days')::interval
    GROUP BY sce.yacht_id, sce.object_type, sce.object_id, LOWER(TRIM(sce.query_text))
    HAVING COUNT(*) >= p_min_clicks
    ORDER BY sce.yacht_id, click_count DESC;
$$;

COMMENT ON FUNCTION public.aggregate_click_events IS
    'Aggregates click events by (yacht_id, object_id, query_text) for counterfactual learning.';

-- ============================================================================
-- PART 5: Apply Learning Function
-- ============================================================================
-- Updates learned_keywords for objects that have learned bridges.
-- Called by nightly worker after aggregation.

CREATE OR REPLACE FUNCTION public.apply_learned_keywords(
    p_yacht_id UUID,
    p_object_type TEXT,
    p_object_id UUID,
    p_keywords TEXT[]
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_keywords_text TEXT;
    v_updated BOOLEAN;
BEGIN
    -- Deduplicate and join keywords
    SELECT string_agg(DISTINCT kw, ' ')
    INTO v_keywords_text
    FROM unnest(p_keywords) AS kw
    WHERE kw IS NOT NULL AND TRIM(kw) != '';

    -- Update search_index (triggers embedding recalculation via content_hash change)
    UPDATE public.search_index
    SET
        learned_keywords = v_keywords_text,
        learned_at = NOW(),
        -- CRITICAL: Change content_hash to trigger embedding re-generation
        content_hash = md5(COALESCE(search_text, '') || ' ' || COALESCE(v_keywords_text, ''))
    WHERE
        yacht_id = p_yacht_id
        AND object_type = p_object_type
        AND object_id = p_object_id
        AND (learned_keywords IS DISTINCT FROM v_keywords_text);

    v_updated := FOUND;

    -- If content changed, mark for re-embedding
    IF v_updated THEN
        UPDATE public.search_index
        SET embedding_status = 'pending'
        WHERE
            yacht_id = p_yacht_id
            AND object_type = p_object_type
            AND object_id = p_object_id;
    END IF;

    RETURN v_updated;
END;
$$;

COMMENT ON FUNCTION public.apply_learned_keywords IS
    'Applies learned vocabulary to search_index and triggers re-embedding.';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
