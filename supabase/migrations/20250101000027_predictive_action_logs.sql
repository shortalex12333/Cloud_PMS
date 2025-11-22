-- ============================================================================
-- PREDICTIVE STATE & ACTION LOGS TABLES
-- ============================================================================
-- predictive_state: Real-time risk scores and signals per equipment
-- action_logs: Audit trail of all system/user actions

-- PREDICTIVE STATE TABLE
CREATE TABLE IF NOT EXISTS public.predictive_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.equipment(id) ON DELETE CASCADE,

    -- Risk Assessment
    risk_score NUMERIC(5,4) NOT NULL DEFAULT 0,  -- 0.0000 to 1.0000
    risk_level TEXT GENERATED ALWAYS AS (
        CASE
            WHEN risk_score >= 0.8 THEN 'critical'
            WHEN risk_score >= 0.6 THEN 'high'
            WHEN risk_score >= 0.4 THEN 'medium'
            WHEN risk_score >= 0.2 THEN 'low'
            ELSE 'minimal'
        END
    ) STORED,

    -- Signals that contribute to risk score
    signals_json JSONB DEFAULT '{}'::jsonb,      -- {signal_name: {value, weight, timestamp}}

    -- Prediction details
    predicted_failure_date DATE,
    confidence NUMERIC(3,2),                     -- 0.00 to 1.00
    model_version TEXT,

    -- Contributing factors
    contributing_faults JSONB DEFAULT '[]'::jsonb,     -- [{fault_id, contribution}]
    contributing_patterns JSONB DEFAULT '[]'::jsonb,   -- [{pattern_name, description}]

    -- Recommendations
    recommended_actions JSONB DEFAULT '[]'::jsonb,     -- [{action, priority, reason}]

    -- Last analysis
    last_analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    analysis_source TEXT DEFAULT 'system',        -- 'system', 'manual', 'scheduled'

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One predictive state per equipment
    CONSTRAINT unique_equipment_predictive UNIQUE (equipment_id)
);

COMMENT ON TABLE public.predictive_state IS 'Real-time predictive maintenance state per equipment';
COMMENT ON COLUMN public.predictive_state.risk_score IS 'Normalized risk score 0-1, computed from signals';
COMMENT ON COLUMN public.predictive_state.signals_json IS 'Input signals: sensor readings, fault frequency, age, etc.';
COMMENT ON COLUMN public.predictive_state.recommended_actions IS 'AI-generated maintenance recommendations';

-- PREDICTIVE HISTORY TABLE (for trend analysis)
CREATE TABLE IF NOT EXISTS public.predictive_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.equipment(id) ON DELETE CASCADE,

    -- Snapshot
    risk_score NUMERIC(5,4) NOT NULL,
    signals_json JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Index hint
    period_bucket TEXT                            -- 'hourly', 'daily', 'weekly' for aggregation
);

COMMENT ON TABLE public.predictive_history IS 'Historical risk score snapshots for trend analysis';

-- ACTION LOGS TABLE (Audit trail)
CREATE TABLE IF NOT EXISTS public.action_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Who & When
    user_id UUID,                                  -- NULL for system actions
    action_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- What
    action_type TEXT NOT NULL,                    -- 'create', 'update', 'delete', 'export', 'search', 'login', etc.
    action_name TEXT NOT NULL,                    -- 'create_work_order', 'add_note', 'export_handover', etc.

    -- Target entity
    entity_type TEXT,                             -- 'work_order', 'note', 'equipment', 'handover', etc.
    entity_id UUID,

    -- Details
    description TEXT,                             -- Human-readable description
    old_values JSONB,                             -- Before state (for updates)
    new_values JSONB,                             -- After state (for creates/updates)

    -- Request context
    request_id UUID,                              -- Correlation ID for tracing
    ip_address INET,
    user_agent TEXT,

    -- Status
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'failed', 'pending')),
    error_message TEXT,

    -- Source
    source TEXT DEFAULT 'api' CHECK (source IN ('api', 'web', 'mobile', 'agent', 'n8n', 'system', 'cron')),

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.action_logs IS 'Audit trail of all system and user actions';
COMMENT ON COLUMN public.action_logs.action_type IS 'General category of action (CRUD, export, etc.)';
COMMENT ON COLUMN public.action_logs.action_name IS 'Specific action name matching API endpoints';

-- SEARCH QUERIES TABLE (for analytics)
CREATE TABLE IF NOT EXISTS public.search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    user_id UUID,

    -- Query
    query_text TEXT NOT NULL,
    interpreted_intent TEXT,                      -- 'diagnose_fault', 'find_manual', 'create_work_order'

    -- Extracted entities
    entities JSONB DEFAULT '{}'::jsonb,           -- {equipment_id, fault_code, part_number, ...}

    -- Results
    result_count INTEGER,
    top_result_type TEXT,                         -- 'document_chunk', 'work_order', 'fault'
    top_result_score NUMERIC(4,3),

    -- Performance
    latency_ms INTEGER,
    retrieval_method TEXT,                        -- 'vector', 'hybrid', 'graph'

    -- Feedback
    was_helpful BOOLEAN,
    feedback_text TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.search_queries IS 'Search query log for analytics and pattern detection';

-- Indexes for predictive_state
CREATE INDEX IF NOT EXISTS idx_predictive_state_yacht_id ON public.predictive_state(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_equipment_id ON public.predictive_state(equipment_id);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk_score ON public.predictive_state(yacht_id, risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_state_risk_level ON public.predictive_state(yacht_id, risk_level);

-- Indexes for predictive_history
CREATE INDEX IF NOT EXISTS idx_predictive_history_yacht_id ON public.predictive_history(yacht_id);
CREATE INDEX IF NOT EXISTS idx_predictive_history_equipment ON public.predictive_history(equipment_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictive_history_time ON public.predictive_history(yacht_id, recorded_at DESC);

-- Indexes for action_logs
CREATE INDEX IF NOT EXISTS idx_action_logs_yacht_id ON public.action_logs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON public.action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_action_type ON public.action_logs(yacht_id, action_type);
CREATE INDEX IF NOT EXISTS idx_action_logs_action_name ON public.action_logs(yacht_id, action_name);
CREATE INDEX IF NOT EXISTS idx_action_logs_entity ON public.action_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_time ON public.action_logs(yacht_id, action_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_logs_request_id ON public.action_logs(request_id);

-- Indexes for search_queries
CREATE INDEX IF NOT EXISTS idx_search_queries_yacht_id ON public.search_queries(yacht_id);
CREATE INDEX IF NOT EXISTS idx_search_queries_user_id ON public.search_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_search_queries_intent ON public.search_queries(yacht_id, interpreted_intent);
CREATE INDEX IF NOT EXISTS idx_search_queries_time ON public.search_queries(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_queries_text_gin ON public.search_queries USING gin (query_text gin_trgm_ops);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 027 Complete - Created predictive_state, predictive_history, action_logs, search_queries tables';
END $$;
