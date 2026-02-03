-- ============================================================================
-- F1 Search Phase 3: Popularity Feedback (Learning-to-Rank feature)
-- ============================================================================
--
-- Tracks search result clicks for popularity scoring.
-- Background job periodically updates popularity_score per (org_id, object_type, object_id).
--
-- GUARDRAILS:
-- - Do NOT ship boosts without evaluation
-- - Start with diagnostics only (Option A)
-- ============================================================================

-- ============================================================================
-- Add popularity_score to search_index
-- ============================================================================

ALTER TABLE search_index
    ADD COLUMN IF NOT EXISTS popularity_score double precision DEFAULT 0;

-- ============================================================================
-- Click Tracking Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_clicks (
    id              bigserial PRIMARY KEY,
    search_id       uuid NOT NULL,
    user_id         uuid NOT NULL,
    org_id          uuid NOT NULL,
    yacht_id        uuid,
    object_type     text NOT NULL,
    object_id       uuid NOT NULL,
    created_at      timestamptz DEFAULT now()
);

-- Index for aggregation queries (by org, by time)
CREATE INDEX IF NOT EXISTS ix_clicks_org
    ON search_clicks (org_id, created_at DESC);

-- Index for per-object aggregation
CREATE INDEX IF NOT EXISTS ix_clicks_object
    ON search_clicks (org_id, object_type, object_id, created_at DESC);

-- ============================================================================
-- Popularity Update Function (called by background job or pg_cron)
-- ============================================================================

-- Lightweight aggregation; run every few minutes via worker or pg_cron
CREATE OR REPLACE FUNCTION update_popularity_scores()
RETURNS void
LANGUAGE sql
AS $$
    WITH agg AS (
        SELECT
            org_id,
            object_type,
            object_id,
            count(*)::double precision AS clicks_7d
        FROM search_clicks
        WHERE created_at > now() - interval '7 days'
        GROUP BY 1, 2, 3
    ),
    norm AS (
        SELECT
            a.org_id,
            a.object_type,
            a.object_id,
            a.clicks_7d / nullif(max(a.clicks_7d) OVER (PARTITION BY a.org_id, a.object_type), 0) AS score
        FROM agg a
    )
    UPDATE search_index si
    SET popularity_score = n.score
    FROM norm n
    WHERE si.org_id = n.org_id
      AND si.object_type = n.object_type
      AND si.object_id = n.object_id;
$$;

-- ============================================================================
-- RLS for search_clicks (same pattern as search_index)
-- ============================================================================

ALTER TABLE search_clicks ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY search_clicks_service_select ON search_clicks
    FOR SELECT TO service_role USING (true);

CREATE POLICY search_clicks_service_insert ON search_clicks
    FOR INSERT TO service_role WITH CHECK (true);

-- Authenticated users: can only see/insert their own org's clicks
CREATE POLICY search_clicks_user_select ON search_clicks
    FOR SELECT TO authenticated
    USING (
        org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid
    );

CREATE POLICY search_clicks_user_insert ON search_clicks
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid
    );

-- ============================================================================
-- Grants
-- ============================================================================

GRANT SELECT, INSERT ON search_clicks TO service_role;
GRANT SELECT, INSERT ON search_clicks TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE search_clicks_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE search_clicks_id_seq TO authenticated;
GRANT EXECUTE ON FUNCTION update_popularity_scores TO service_role;
