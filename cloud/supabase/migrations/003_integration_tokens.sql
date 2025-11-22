-- ============================================================================
-- Migration: 003_integration_tokens.sql
-- Description: Add integration tokens table for third-party OAuth connections
--              (Microsoft/Outlook, Google, etc.)
-- ============================================================================

-- Integration tokens table for OAuth providers
CREATE TABLE integration_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('microsoft', 'google', 'dropbox')),

    -- OAuth client info
    client_id TEXT,                          -- OAuth app client ID used

    -- OAuth tokens
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ NOT NULL,

    -- Provider-specific data
    provider_user_id TEXT,                   -- User ID from provider
    provider_email TEXT NOT NULL,            -- Email from provider (e.g., Outlook email)
    display_name TEXT,
    scopes TEXT[],                           -- Granted OAuth scopes

    -- Token status
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,  -- Set false if refresh fails
    last_used_at TIMESTAMPTZ,
    last_refresh_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One integration per user per provider
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX idx_integration_tokens_user_id ON integration_tokens(user_id);
CREATE INDEX idx_integration_tokens_yacht_id ON integration_tokens(yacht_id);
CREATE INDEX idx_integration_tokens_provider ON integration_tokens(provider);
CREATE INDEX idx_integration_tokens_provider_email ON integration_tokens(provider_email);
CREATE INDEX idx_integration_tokens_expires ON integration_tokens(expires_at);
CREATE INDEX idx_integration_tokens_valid ON integration_tokens(is_valid) WHERE is_valid = TRUE;

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
          AND is_valid = TRUE
          AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function for n8n to get token by provider email
-- Returns access_token, refresh_token, expires_at for a given email and provider
CREATE OR REPLACE FUNCTION get_integration_token(
    p_provider_email TEXT,
    p_provider TEXT DEFAULT 'microsoft'
)
RETURNS TABLE (
    user_id UUID,
    yacht_id UUID,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    is_valid BOOLEAN
) AS $$
BEGIN
    -- Update last_used_at
    UPDATE integration_tokens it
    SET last_used_at = NOW()
    WHERE it.provider_email = p_provider_email
      AND it.provider = p_provider
      AND it.is_valid = TRUE;

    RETURN QUERY
    SELECT
        it.user_id,
        it.yacht_id,
        it.access_token,
        it.refresh_token,
        it.expires_at,
        it.is_valid
    FROM integration_tokens it
    WHERE it.provider_email = p_provider_email
      AND it.provider = p_provider
      AND it.is_valid = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to update tokens after refresh
CREATE OR REPLACE FUNCTION update_integration_token(
    p_provider_email TEXT,
    p_provider TEXT,
    p_access_token TEXT,
    p_refresh_token TEXT,
    p_expires_at TIMESTAMPTZ
)
RETURNS BOOLEAN AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE integration_tokens
    SET access_token = p_access_token,
        refresh_token = COALESCE(p_refresh_token, refresh_token),
        expires_at = p_expires_at,
        last_refresh_at = NOW(),
        is_valid = TRUE
    WHERE provider_email = p_provider_email
      AND provider = p_provider;

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to invalidate a token (when refresh fails permanently)
CREATE OR REPLACE FUNCTION invalidate_integration_token(
    p_provider_email TEXT,
    p_provider TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE integration_tokens
    SET is_valid = FALSE
    WHERE provider_email = p_provider_email
      AND provider = p_provider;

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE integration_tokens IS 'Stores OAuth tokens for third-party integrations (Microsoft, Google, etc.)';
COMMENT ON FUNCTION user_has_integration IS 'Check if user has a valid integration connection';
COMMENT ON FUNCTION get_integration_token IS 'Get OAuth token by provider email (for n8n workflows)';
COMMENT ON FUNCTION update_integration_token IS 'Update tokens after OAuth refresh';
COMMENT ON FUNCTION invalidate_integration_token IS 'Mark token as invalid when refresh fails';
