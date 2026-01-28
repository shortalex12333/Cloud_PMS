-- =============================================================================
-- Lens Ops Health Monitoring Tables
-- =============================================================================
--
-- Purpose: Production-grade health monitoring for all lenses
--
-- Tables:
-- - pms_health_checks: Aggregated health check results (one row per check)
-- - pms_health_events: Detailed event logs (many events per check)
--
-- RLS: Yacht-scoped (users can only see their yacht's health checks)
-- Service role: Can write health checks from background workers
--
-- Usage:
-- - Background workers write to these tables every N minutes
-- - Ops dashboard queries these tables for health status
-- - Alerts triggered on 'unhealthy' status or high error rates
--
-- =============================================================================

-- Health Checks Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS pms_health_checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id uuid NOT NULL,
    lens_id text NOT NULL,  -- e.g., 'faults', 'certificates', 'equipment'
    status text NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    p95_latency_ms integer,  -- 95th percentile latency in milliseconds
    error_rate_percent numeric(5,2),  -- Error rate as percentage (0.00-100.00)
    sample_size integer,  -- Number of requests in this check
    observed_at timestamp with time zone NOT NULL DEFAULT now(),
    notes jsonb DEFAULT '{}'::jsonb  -- Detailed check results (JSON)
    -- NOTE: FK to yacht_registry removed (table doesn't exist in tenant)
    -- RLS + indexes enforce yacht isolation; FK can be added later if needed
);

COMMENT ON TABLE pms_health_checks IS 'Aggregated health check results from lens monitoring workers';
COMMENT ON COLUMN pms_health_checks.lens_id IS 'Lens identifier (e.g., faults, certificates, equipment)';
COMMENT ON COLUMN pms_health_checks.status IS 'Overall health status: healthy (all green), degraded (some warnings), unhealthy (errors/5xx)';
COMMENT ON COLUMN pms_health_checks.p95_latency_ms IS '95th percentile latency for requests in this check';
COMMENT ON COLUMN pms_health_checks.error_rate_percent IS 'Percentage of requests that returned 4xx/5xx';
COMMENT ON COLUMN pms_health_checks.sample_size IS 'Number of requests tested in this check';
COMMENT ON COLUMN pms_health_checks.notes IS 'Detailed check results (endpoint statuses, feature flags, etc.)';

-- Indexes for efficient querying
CREATE INDEX idx_health_checks_yacht_lens ON pms_health_checks (yacht_id, lens_id);
CREATE INDEX idx_health_checks_observed ON pms_health_checks (observed_at DESC);
CREATE INDEX idx_health_checks_status ON pms_health_checks (status, observed_at DESC);

-- Health Events Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS pms_health_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    check_id uuid NOT NULL,
    level text NOT NULL CHECK (level IN ('info', 'warning', 'error')),
    detail_json jsonb NOT NULL,  -- Event-specific details
    created_at timestamp with time zone NOT NULL DEFAULT now(),

    -- Foreign keys
    CONSTRAINT fk_check FOREIGN KEY (check_id)
        REFERENCES pms_health_checks(id) ON DELETE CASCADE
);

COMMENT ON TABLE pms_health_events IS 'Detailed event logs for health checks (warnings, errors, info)';
COMMENT ON COLUMN pms_health_events.check_id IS 'Parent health check ID';
COMMENT ON COLUMN pms_health_events.level IS 'Event severity: info (informational), warning (degraded), error (unhealthy)';
COMMENT ON COLUMN pms_health_events.detail_json IS 'Event-specific details (error messages, endpoint failures, etc.)';

-- Indexes for efficient querying
CREATE INDEX idx_health_events_check ON pms_health_events (check_id);
CREATE INDEX idx_health_events_level ON pms_health_events (level, created_at DESC);

-- RLS Policies
-- =============================================================================

-- Enable RLS on both tables
ALTER TABLE pms_health_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_health_events ENABLE ROW LEVEL SECURITY;

-- Yacht-scoped SELECT for authenticated users
-- Users can only see health checks for their own yacht
CREATE POLICY "yacht_scoped_health_checks"
    ON pms_health_checks
    FOR SELECT
    TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- Service role can write health checks (from background workers)
-- Background workers run with service_role credentials
CREATE POLICY "service_role_write_health_checks"
    ON pms_health_checks
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Yacht-scoped SELECT for health events (via parent check)
-- Users can only see events for health checks belonging to their yacht
CREATE POLICY "yacht_scoped_health_events"
    ON pms_health_events
    FOR SELECT
    TO authenticated
    USING (
        check_id IN (
            SELECT id FROM pms_health_checks WHERE yacht_id = get_user_yacht_id()
        )
    );

-- Service role can write health events (from background workers)
CREATE POLICY "service_role_write_health_events"
    ON pms_health_events
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Helper Functions (Optional)
-- =============================================================================

-- Get latest health check for a lens
CREATE OR REPLACE FUNCTION get_latest_health_check(p_yacht_id uuid, p_lens_id text)
RETURNS TABLE (
    id uuid,
    status text,
    p95_latency_ms integer,
    error_rate_percent numeric,
    observed_at timestamp with time zone,
    notes jsonb
)
LANGUAGE sql
STABLE
AS $$
    SELECT id, status, p95_latency_ms, error_rate_percent, observed_at, notes
    FROM pms_health_checks
    WHERE yacht_id = p_yacht_id
      AND lens_id = p_lens_id
    ORDER BY observed_at DESC
    LIMIT 1;
$$;

COMMENT ON FUNCTION get_latest_health_check IS 'Get most recent health check for a specific lens';

-- Get health check history for a lens (last 24h)
CREATE OR REPLACE FUNCTION get_health_check_history(p_yacht_id uuid, p_lens_id text, p_hours integer DEFAULT 24)
RETURNS TABLE (
    id uuid,
    status text,
    p95_latency_ms integer,
    error_rate_percent numeric,
    observed_at timestamp with time zone
)
LANGUAGE sql
STABLE
AS $$
    SELECT id, status, p95_latency_ms, error_rate_percent, observed_at
    FROM pms_health_checks
    WHERE yacht_id = p_yacht_id
      AND lens_id = p_lens_id
      AND observed_at >= now() - (p_hours || ' hours')::interval
    ORDER BY observed_at DESC;
$$;

COMMENT ON FUNCTION get_health_check_history IS 'Get health check history for a lens (default: last 24 hours)';

-- Get unhealthy lenses for a yacht
CREATE OR REPLACE FUNCTION get_unhealthy_lenses(p_yacht_id uuid)
RETURNS TABLE (
    lens_id text,
    status text,
    last_observed timestamp with time zone,
    error_count bigint
)
LANGUAGE sql
STABLE
AS $$
    WITH latest_checks AS (
        SELECT DISTINCT ON (lens_id)
            lens_id,
            status,
            observed_at AS last_observed
        FROM pms_health_checks
        WHERE yacht_id = p_yacht_id
        ORDER BY lens_id, observed_at DESC
    )
    SELECT
        lc.lens_id,
        lc.status,
        lc.last_observed,
        COUNT(he.id) AS error_count
    FROM latest_checks lc
    LEFT JOIN pms_health_checks hc ON hc.yacht_id = p_yacht_id AND hc.lens_id = lc.lens_id
    LEFT JOIN pms_health_events he ON he.check_id = hc.id AND he.level = 'error'
    WHERE lc.status IN ('degraded', 'unhealthy')
    GROUP BY lc.lens_id, lc.status, lc.last_observed
    ORDER BY lc.last_observed DESC;
$$;

COMMENT ON FUNCTION get_unhealthy_lenses IS 'Get all lenses with degraded/unhealthy status for a yacht';

-- Example Queries
-- =============================================================================

-- Get latest health status for all lenses (current yacht)
-- SELECT * FROM get_latest_health_check(get_user_yacht_id(), 'faults');

-- Get health history for faults lens (last 24h)
-- SELECT * FROM get_health_check_history(get_user_yacht_id(), 'faults', 24);

-- Get all unhealthy lenses for current yacht
-- SELECT * FROM get_unhealthy_lenses(get_user_yacht_id());

-- Get recent error events for faults lens
-- SELECT he.*
-- FROM pms_health_events he
-- JOIN pms_health_checks hc ON he.check_id = hc.id
-- WHERE hc.yacht_id = get_user_yacht_id()
--   AND hc.lens_id = 'faults'
--   AND he.level = 'error'
--   AND he.created_at >= now() - interval '1 hour'
-- ORDER BY he.created_at DESC;

-- =============================================================================
-- End of Migration
-- =============================================================================
