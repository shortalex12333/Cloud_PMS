-- CelesteOS Snapshot Tables Migration
-- Version: 1.0
-- Purpose: Dashboard snapshot tables, predictive state, and support tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ============================================================================
-- ENUMS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE risk_level AS ENUM ('normal', 'monitor', 'emerging', 'high', 'critical');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE action_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE insight_type AS ENUM ('threshold_alert', 'pattern_detected', 'trend_warning', 'crew_frustration', 'inventory_gap', 'compliance_due');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE snapshot_type AS ENUM ('briefing', 'legacy', 'predictive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- PREDICTIVE STATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS predictive_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,

    -- Risk scoring
    risk_score NUMERIC(5,4) NOT NULL DEFAULT 0.0 CHECK (risk_score >= 0 AND risk_score <= 1),
    risk_level risk_level GENERATED ALWAYS AS (
        CASE
            WHEN risk_score >= 0.75 THEN 'critical'::risk_level
            WHEN risk_score >= 0.60 THEN 'high'::risk_level
            WHEN risk_score >= 0.45 THEN 'emerging'::risk_level
            WHEN risk_score >= 0.30 THEN 'monitor'::risk_level
            ELSE 'normal'::risk_level
        END
    ) STORED,

    -- Confidence and trend
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.25 CHECK (confidence >= 0 AND confidence <= 1),
    trend TEXT CHECK (trend IN ('improving', 'stable', 'worsening')),
    trend_delta NUMERIC(5,4) DEFAULT 0,

    -- Contributing factors (JSON structure)
    contributing_factors JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    last_calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previous_risk_score NUMERIC(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint per yacht/equipment
    UNIQUE(yacht_id, equipment_id)
);

-- Indexes for predictive_state
CREATE INDEX IF NOT EXISTS idx_predictive_state_yacht ON predictive_state(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk ON predictive_state(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_state_level ON predictive_state(risk_level);
CREATE INDEX IF NOT EXISTS idx_predictive_state_updated ON predictive_state(updated_at DESC);

-- ============================================================================
-- PREDICTIVE INSIGHTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS predictive_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,

    -- Insight details
    insight_type insight_type NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- State tracking
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    dismissed BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,

    -- Lifecycle
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for predictive_insights
CREATE INDEX IF NOT EXISTS idx_predictive_insights_yacht ON predictive_insights(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_equipment ON predictive_insights(equipment_id);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_type ON predictive_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_severity ON predictive_insights(severity);
CREATE INDEX IF NOT EXISTS idx_predictive_insights_active ON predictive_insights(yacht_id, dismissed, acknowledged)
    WHERE dismissed = FALSE;

-- ============================================================================
-- DASHBOARD SNAPSHOT TABLE (Intelligence Briefing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_snapshot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    snapshot_type snapshot_type NOT NULL DEFAULT 'briefing',

    -- High risk equipment (array of equipment summaries)
    high_risk_equipment JSONB NOT NULL DEFAULT '[]',

    -- Risk movements today
    risk_movements JSONB NOT NULL DEFAULT '[]',

    -- Unstable systems (48h window)
    unstable_systems JSONB NOT NULL DEFAULT '[]',

    -- 7-day patterns
    patterns_7d JSONB NOT NULL DEFAULT '[]',

    -- Overdue work orders
    overdue_critical JSONB NOT NULL DEFAULT '[]',

    -- Inventory gaps
    inventory_gaps JSONB NOT NULL DEFAULT '[]',

    -- Inspections due
    inspections_due JSONB NOT NULL DEFAULT '[]',

    -- Crew frustration (search clusters)
    crew_frustration JSONB NOT NULL DEFAULT '[]',

    -- Summary stats
    summary_stats JSONB NOT NULL DEFAULT '{}',

    -- Generation metadata
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generation_duration_ms INTEGER,
    data_freshness_hours NUMERIC(5,2),

    -- Validity
    valid_until TIMESTAMPTZ,
    is_stale BOOLEAN GENERATED ALWAYS AS (valid_until < NOW()) STORED
);

-- Indexes for dashboard_snapshot
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_yacht ON dashboard_snapshot(yacht_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_type ON dashboard_snapshot(snapshot_type);
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_generated ON dashboard_snapshot(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_active ON dashboard_snapshot(yacht_id, snapshot_type, generated_at DESC);

-- ============================================================================
-- DASHBOARD LEGACY VIEW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_legacy_view (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- Equipment overview
    equipment_overview JSONB NOT NULL DEFAULT '[]',
    equipment_count INTEGER DEFAULT 0,
    equipment_by_status JSONB DEFAULT '{}',

    -- Work orders overview
    work_orders_overview JSONB NOT NULL DEFAULT '[]',
    work_orders_count INTEGER DEFAULT 0,
    work_orders_by_status JSONB DEFAULT '{}',
    work_orders_overdue_count INTEGER DEFAULT 0,

    -- Inventory overview
    inventory_overview JSONB NOT NULL DEFAULT '[]',
    inventory_count INTEGER DEFAULT 0,
    inventory_low_stock_count INTEGER DEFAULT 0,

    -- Certificates overview
    certificates_overview JSONB NOT NULL DEFAULT '[]',
    certificates_count INTEGER DEFAULT 0,
    certificates_expiring_soon INTEGER DEFAULT 0,

    -- Fault history
    fault_history JSONB NOT NULL DEFAULT '[]',
    faults_active_count INTEGER DEFAULT 0,
    faults_resolved_30d INTEGER DEFAULT 0,

    -- Scheduled maintenance
    scheduled_maintenance JSONB NOT NULL DEFAULT '[]',
    maintenance_upcoming_7d INTEGER DEFAULT 0,
    maintenance_overdue INTEGER DEFAULT 0,

    -- Parts usage
    parts_usage JSONB NOT NULL DEFAULT '[]',

    -- Documents summary
    documents_summary JSONB NOT NULL DEFAULT '{}',
    documents_total INTEGER DEFAULT 0,

    -- Generation metadata
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,

    UNIQUE(yacht_id)
);

-- Indexes for dashboard_legacy_view
CREATE INDEX IF NOT EXISTS idx_dashboard_legacy_yacht ON dashboard_legacy_view(yacht_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_legacy_generated ON dashboard_legacy_view(generated_at DESC);

-- ============================================================================
-- ACTION LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS action_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Action details
    action_name TEXT NOT NULL,
    action_status action_status NOT NULL DEFAULT 'pending',

    -- Request/Response
    request_payload JSONB NOT NULL DEFAULT '{}',
    response_payload JSONB,

    -- Context
    context JSONB DEFAULT '{}',

    -- Error tracking
    error_code TEXT,
    error_message TEXT,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Source tracking
    source_ip TEXT,
    user_agent TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for action_logs
CREATE INDEX IF NOT EXISTS idx_action_logs_yacht ON action_logs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_user ON action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_action ON action_logs(action_name);
CREATE INDEX IF NOT EXISTS idx_action_logs_status ON action_logs(action_status);
CREATE INDEX IF NOT EXISTS idx_action_logs_created ON action_logs(created_at DESC);

-- ============================================================================
-- PIPELINE LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS pipeline_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID REFERENCES yachts(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Pipeline step
    step TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('info', 'warning', 'retry', 'failed', 'success')),

    -- Details
    message TEXT,
    error_details JSONB,
    metadata JSONB DEFAULT '{}',

    -- Timing
    duration_ms INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for pipeline_logs
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_yacht ON pipeline_logs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_document ON pipeline_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_step ON pipeline_logs(step);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_status ON pipeline_logs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_created ON pipeline_logs(created_at DESC);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Notification content
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL,
    priority TEXT CHECK (priority IN ('low', 'normal', 'high', 'critical')) DEFAULT 'normal',

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- State
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    dismissed BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,

    -- Delivery
    delivered_push BOOLEAN DEFAULT FALSE,
    delivered_email BOOLEAN DEFAULT FALSE,

    -- Lifecycle
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for notifications
CREATE INDEX IF NOT EXISTS idx_notifications_yacht ON notifications(yacht_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, read) WHERE read = FALSE;
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- ============================================================================
-- SEARCH SUGGESTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE CASCADE,

    -- Suggestion content
    suggestion_text TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    category TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Lifecycle
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicates
    UNIQUE(yacht_id, suggestion_text)
);

-- Indexes for search_suggestions
CREATE INDEX IF NOT EXISTS idx_search_suggestions_yacht ON search_suggestions(yacht_id);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_priority ON search_suggestions(priority DESC);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_active ON search_suggestions(yacht_id, expires_at)
    WHERE expires_at > NOW() OR expires_at IS NULL;

-- ============================================================================
-- SYSTEM LOGS TABLE (for workflow tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for system_logs
CREATE INDEX IF NOT EXISTS idx_system_logs_type ON system_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_system_logs_created ON system_logs(created_at DESC);

-- ============================================================================
-- NOTES TABLE (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    note_text TEXT NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for notes
CREATE INDEX IF NOT EXISTS idx_notes_yacht ON notes(yacht_id);
CREATE INDEX IF NOT EXISTS idx_notes_equipment ON notes(equipment_id);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at DESC);

-- ============================================================================
-- HANDOVER ITEMS TABLE (extended)
-- ============================================================================

-- Add missing columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'equipment_id') THEN
        ALTER TABLE handover_items ADD COLUMN equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'title') THEN
        ALTER TABLE handover_items ADD COLUMN title TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'description') THEN
        ALTER TABLE handover_items ADD COLUMN description TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'priority') THEN
        ALTER TABLE handover_items ADD COLUMN priority TEXT DEFAULT 'normal';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'status') THEN
        ALTER TABLE handover_items ADD COLUMN status TEXT DEFAULT 'pending';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'source') THEN
        ALTER TABLE handover_items ADD COLUMN source TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'handover_items' AND column_name = 'source_id') THEN
        ALTER TABLE handover_items ADD COLUMN source_id UUID;
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        -- Table doesn't exist, will be created by table_configs
        NULL;
END $$;

-- ============================================================================
-- EQUIPMENT EXTENSIONS (for attention flags)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'equipment' AND column_name = 'attention_flag') THEN
        ALTER TABLE equipment ADD COLUMN attention_flag BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'equipment' AND column_name = 'attention_reason') THEN
        ALTER TABLE equipment ADD COLUMN attention_reason TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'equipment' AND column_name = 'attention_updated_at') THEN
        ALTER TABLE equipment ADD COLUMN attention_updated_at TIMESTAMPTZ;
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        NULL;
END $$;

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE predictive_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictive_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_legacy_view ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

-- RLS Policies for predictive_state
DROP POLICY IF EXISTS predictive_state_yacht_isolation ON predictive_state;
CREATE POLICY predictive_state_yacht_isolation ON predictive_state
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for predictive_insights
DROP POLICY IF EXISTS predictive_insights_yacht_isolation ON predictive_insights;
CREATE POLICY predictive_insights_yacht_isolation ON predictive_insights
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for dashboard_snapshot
DROP POLICY IF EXISTS dashboard_snapshot_yacht_isolation ON dashboard_snapshot;
CREATE POLICY dashboard_snapshot_yacht_isolation ON dashboard_snapshot
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for dashboard_legacy_view
DROP POLICY IF EXISTS dashboard_legacy_yacht_isolation ON dashboard_legacy_view;
CREATE POLICY dashboard_legacy_yacht_isolation ON dashboard_legacy_view
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for action_logs
DROP POLICY IF EXISTS action_logs_yacht_isolation ON action_logs;
CREATE POLICY action_logs_yacht_isolation ON action_logs
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for notifications
DROP POLICY IF EXISTS notifications_user_isolation ON notifications;
CREATE POLICY notifications_user_isolation ON notifications
    FOR ALL
    USING (user_id = auth.uid() OR yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for search_suggestions
DROP POLICY IF EXISTS search_suggestions_yacht_isolation ON search_suggestions;
CREATE POLICY search_suggestions_yacht_isolation ON search_suggestions
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- RLS Policies for notes
DROP POLICY IF EXISTS notes_yacht_isolation ON notes;
CREATE POLICY notes_yacht_isolation ON notes
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM users WHERE id = auth.uid()
    ));

-- ============================================================================
-- FUNCTIONS FOR DASHBOARD QUERIES
-- ============================================================================

-- Function to get latest dashboard snapshot
CREATE OR REPLACE FUNCTION get_latest_dashboard_snapshot(p_yacht_id UUID, p_type snapshot_type DEFAULT 'briefing')
RETURNS SETOF dashboard_snapshot AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM dashboard_snapshot
    WHERE yacht_id = p_yacht_id
      AND snapshot_type = p_type
      AND (valid_until IS NULL OR valid_until > NOW())
    ORDER BY generated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get high risk equipment
CREATE OR REPLACE FUNCTION get_high_risk_equipment(p_yacht_id UUID, p_threshold NUMERIC DEFAULT 0.6)
RETURNS TABLE (
    equipment_id UUID,
    equipment_name TEXT,
    risk_score NUMERIC,
    risk_level risk_level,
    trend TEXT,
    contributing_factors JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.equipment_id,
        e.name as equipment_name,
        ps.risk_score,
        ps.risk_level,
        ps.trend,
        ps.contributing_factors
    FROM predictive_state ps
    JOIN equipment e ON ps.equipment_id = e.id
    WHERE ps.yacht_id = p_yacht_id
      AND ps.risk_score >= p_threshold
    ORDER BY ps.risk_score DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get risk movements (today)
CREATE OR REPLACE FUNCTION get_risk_movements(p_yacht_id UUID)
RETURNS TABLE (
    equipment_id UUID,
    equipment_name TEXT,
    current_score NUMERIC,
    previous_score NUMERIC,
    delta NUMERIC,
    direction TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.equipment_id,
        e.name as equipment_name,
        ps.risk_score as current_score,
        ps.previous_risk_score as previous_score,
        (ps.risk_score - COALESCE(ps.previous_risk_score, 0)) as delta,
        CASE
            WHEN ps.risk_score > COALESCE(ps.previous_risk_score, 0) THEN 'up'
            WHEN ps.risk_score < COALESCE(ps.previous_risk_score, 0) THEN 'down'
            ELSE 'stable'
        END as direction
    FROM predictive_state ps
    JOIN equipment e ON ps.equipment_id = e.id
    WHERE ps.yacht_id = p_yacht_id
      AND ps.updated_at >= CURRENT_DATE
      AND ABS(ps.risk_score - COALESCE(ps.previous_risk_score, 0)) > 0.05
    ORDER BY ABS(ps.risk_score - COALESCE(ps.previous_risk_score, 0)) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger to update previous_risk_score before updating predictive_state
CREATE OR REPLACE FUNCTION update_previous_risk_score()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.risk_score IS DISTINCT FROM NEW.risk_score THEN
        NEW.previous_risk_score := OLD.risk_score;
        NEW.trend_delta := NEW.risk_score - OLD.risk_score;
        NEW.trend := CASE
            WHEN NEW.risk_score > OLD.risk_score + 0.02 THEN 'worsening'
            WHEN NEW.risk_score < OLD.risk_score - 0.02 THEN 'improving'
            ELSE 'stable'
        END;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_previous_risk ON predictive_state;
CREATE TRIGGER trigger_update_previous_risk
    BEFORE UPDATE ON predictive_state
    FOR EACH ROW
    EXECUTE FUNCTION update_previous_risk_score();

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_notes_updated_at ON notes;
CREATE TRIGGER trigger_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for active insights (not dismissed)
CREATE OR REPLACE VIEW v_active_insights AS
SELECT
    pi.*,
    e.name as equipment_name,
    e.system_type,
    e.criticality
FROM predictive_insights pi
LEFT JOIN equipment e ON pi.equipment_id = e.id
WHERE pi.dismissed = FALSE
  AND (pi.expires_at IS NULL OR pi.expires_at > NOW());

-- View for equipment with risk status
CREATE OR REPLACE VIEW v_equipment_risk AS
SELECT
    e.*,
    COALESCE(ps.risk_score, 0) as risk_score,
    COALESCE(ps.risk_level, 'normal') as risk_level,
    ps.trend,
    ps.contributing_factors,
    ps.last_calculated_at as risk_calculated_at
FROM equipment e
LEFT JOIN predictive_state ps ON e.id = ps.equipment_id;

-- ============================================================================
-- GRANT PERMISSIONS (for service role)
-- ============================================================================

GRANT ALL ON predictive_state TO service_role;
GRANT ALL ON predictive_insights TO service_role;
GRANT ALL ON dashboard_snapshot TO service_role;
GRANT ALL ON dashboard_legacy_view TO service_role;
GRANT ALL ON action_logs TO service_role;
GRANT ALL ON pipeline_logs TO service_role;
GRANT ALL ON notifications TO service_role;
GRANT ALL ON search_suggestions TO service_role;
GRANT ALL ON system_logs TO service_role;
GRANT ALL ON notes TO service_role;

GRANT SELECT ON v_active_insights TO authenticated;
GRANT SELECT ON v_equipment_risk TO authenticated;

GRANT EXECUTE ON FUNCTION get_latest_dashboard_snapshot TO authenticated;
GRANT EXECUTE ON FUNCTION get_high_risk_equipment TO authenticated;
GRANT EXECUTE ON FUNCTION get_risk_movements TO authenticated;

-- ============================================================================
-- COMPLETED
-- ============================================================================
