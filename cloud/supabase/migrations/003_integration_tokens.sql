-- ============================================================================
-- Migration: 003_integration_tokens.sql
-- Description: Add integration tokens table for third-party OAuth connections
--              (Microsoft/Outlook, Google, etc.)
-- ============================================================================

-- Integration tokens table for OAuth providers
CREATE TABLE integration_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('microsoft', 'google', 'dropbox')),

    -- OAuth tokens
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ NOT NULL,

    -- Provider-specific data
    provider_user_id TEXT,
    provider_email TEXT,
    display_name TEXT,
    scopes TEXT[],

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One integration per user per provider
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX idx_integration_tokens_user_id ON integration_tokens(user_id);
CREATE INDEX idx_integration_tokens_provider ON integration_tokens(provider);
CREATE INDEX idx_integration_tokens_expires ON integration_tokens(expires_at);

-- RLS Policies
ALTER TABLE integration_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only access their own tokens
CREATE POLICY "Users can access own integration tokens"
    ON integration_tokens
    FOR ALL
    USING (user_id = auth.uid());

-- Service role has full access (for n8n workflows)
CREATE POLICY "Service role has full access to integration tokens"
    ON integration_tokens
    FOR ALL
    TO service_role
    USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_integration_tokens_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER integration_tokens_updated_at
    BEFORE UPDATE ON integration_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_integration_tokens_updated_at();

-- Helper function to check if user has a connected integration
CREATE OR REPLACE FUNCTION user_has_integration(
    p_user_id UUID,
    p_provider TEXT
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM integration_tokens
        WHERE user_id = p_user_id
          AND provider = p_provider
          AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE integration_tokens IS 'Stores OAuth tokens for third-party integrations (Microsoft, Google, etc.)';
COMMENT ON FUNCTION user_has_integration IS 'Check if user has a valid integration connection';
