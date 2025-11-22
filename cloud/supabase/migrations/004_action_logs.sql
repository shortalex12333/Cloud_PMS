-- ============================================================================
-- Action Logs Table
-- Stores execution logs for all micro-actions dispatched through the API
-- ============================================================================

-- Create action_logs table
CREATE TABLE IF NOT EXISTS action_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Action details
    action_name VARCHAR(100) NOT NULL,
    action_payload JSONB NOT NULL DEFAULT '{}',
    handler_type VARCHAR(20) NOT NULL DEFAULT 'n8n',  -- 'n8n' or 'internal'

    -- Execution status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, stubbed, success, error
    error_message TEXT,
    n8n_response JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'stubbed', 'success', 'error')),
    CONSTRAINT valid_handler_type CHECK (handler_type IN ('n8n', 'internal'))
);

-- Create indexes for common queries
CREATE INDEX idx_action_logs_yacht_id ON action_logs(yacht_id);
CREATE INDEX idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX idx_action_logs_action_name ON action_logs(action_name);
CREATE INDEX idx_action_logs_status ON action_logs(status);
CREATE INDEX idx_action_logs_created_at ON action_logs(created_at DESC);

-- Composite index for yacht + action queries
CREATE INDEX idx_action_logs_yacht_action ON action_logs(yacht_id, action_name, created_at DESC);

-- ============================================================================
-- Row Level Security
-- ============================================================================

-- Enable RLS
ALTER TABLE action_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own yacht's action logs
CREATE POLICY "Users can view own yacht action logs"
    ON action_logs FOR SELECT
    USING (
        yacht_id IN (
            SELECT uy.yacht_id
            FROM users_yacht uy
            WHERE uy.user_id = auth.uid()
        )
    );

-- Policy: Service role can do everything (for n8n and internal operations)
CREATE POLICY "Service role has full access to action logs"
    ON action_logs FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE action_logs IS 'Execution logs for micro-actions dispatched through the Action Router API';
COMMENT ON COLUMN action_logs.action_name IS 'Name of the action from ACTION_REGISTRY (e.g., create_work_order, add_note)';
COMMENT ON COLUMN action_logs.action_payload IS 'Combined context + payload fields passed to the action';
COMMENT ON COLUMN action_logs.handler_type IS 'Handler type: n8n for webhook dispatch, internal for API-handled';
COMMENT ON COLUMN action_logs.status IS 'Execution status: pending (queued), stubbed (dev mode), success, error';
COMMENT ON COLUMN action_logs.n8n_response IS 'Response from n8n webhook if applicable';
