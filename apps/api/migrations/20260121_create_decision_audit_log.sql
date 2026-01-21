-- Decision Audit Log Table
-- Phase 11.3: Logs all decision evaluations per E021 spec
--
-- Purpose:
-- - Explainability: "Why was this action shown/hidden?"
-- - Analytics: Confidence distribution, common blocks
-- - Compliance: Full audit trail of AI decisions
--
-- Run this migration on each TENANT database (not MASTER)

-- Create table
CREATE TABLE IF NOT EXISTS decision_audit_log (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Execution context
    execution_id UUID NOT NULL,  -- Groups decisions from same evaluation
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- User context
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    session_id UUID,
    user_role TEXT,

    -- Decision details
    action TEXT NOT NULL,
    decision TEXT NOT NULL,  -- 'show', 'hide', 'disable'
    tier TEXT,  -- 'primary', 'conditional', 'rare'

    -- Confidence scores (E018)
    confidence_total FLOAT DEFAULT 0.0,
    confidence_intent FLOAT DEFAULT 0.0,
    confidence_entity FLOAT DEFAULT 0.0,
    confidence_situation FLOAT DEFAULT 0.0,

    -- Why the decision was made
    reasons JSONB DEFAULT '[]'::jsonb,
    blocked_by TEXT,
    blocked_by_type TEXT,  -- 'state_guard', 'forbidden', 'threshold', 'permission'

    -- Context snapshot
    detected_intents JSONB DEFAULT '[]'::jsonb,
    entities JSONB DEFAULT '[]'::jsonb,
    situation JSONB DEFAULT '{}'::jsonb,
    environment TEXT DEFAULT 'at_sea'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_decision_audit_execution
    ON decision_audit_log(execution_id);

CREATE INDEX IF NOT EXISTS idx_decision_audit_user
    ON decision_audit_log(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_decision_audit_yacht
    ON decision_audit_log(yacht_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_decision_audit_action
    ON decision_audit_log(action, decision);

CREATE INDEX IF NOT EXISTS idx_decision_audit_timestamp
    ON decision_audit_log(timestamp DESC);

-- Composite index for common analytics queries
CREATE INDEX IF NOT EXISTS idx_decision_audit_analytics
    ON decision_audit_log(yacht_id, action, decision, timestamp DESC);

-- Enable RLS (Row Level Security)
ALTER TABLE decision_audit_log ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their yacht's decisions
CREATE POLICY "Users can view their yacht decisions"
    ON decision_audit_log
    FOR SELECT
    USING (yacht_id = auth.jwt() ->> 'yacht_id');

-- Service role can insert (backend)
CREATE POLICY "Service role can insert"
    ON decision_audit_log
    FOR INSERT
    WITH CHECK (true);

-- Service role can select all (for admin/analytics)
CREATE POLICY "Service role can select"
    ON decision_audit_log
    FOR SELECT
    USING (auth.role() = 'service_role');

-- Comment for documentation
COMMENT ON TABLE decision_audit_log IS
    'Decision Engine audit log per E021 spec. Logs all action decisions with confidence scores and context.';

COMMENT ON COLUMN decision_audit_log.execution_id IS
    'UUID grouping all decisions from a single evaluation call';

COMMENT ON COLUMN decision_audit_log.decision IS
    'Outcome: show (allowed), hide (blocked/low confidence), disable (blocked but shown)';

COMMENT ON COLUMN decision_audit_log.confidence_total IS
    'E018 weighted sum: intent*0.4 + entity*0.4 + situation*0.2';
