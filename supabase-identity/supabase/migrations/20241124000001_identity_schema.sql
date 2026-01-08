-- ============================================================================
-- CELESTE7 IDENTITY PROJECT - Core Schema
-- Project: qvzmkaamzaqxpzbewjxe
-- Purpose: Yacht registration, activation, and credential management
-- Security Level: HIGHEST - Contains shared_secret (crown jewels)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- FLEET REGISTRY TABLE
-- Central table for yacht identity and credentials
-- ============================================================================

CREATE TABLE IF NOT EXISTS fleet_registry (
    -- Primary identifier
    yacht_id TEXT PRIMARY KEY,

    -- SHA256 hash of yacht_id (for verification without exposing ID)
    yacht_id_hash CHAR(64) NOT NULL UNIQUE,

    -- Buyer/owner information
    buyer_email TEXT NOT NULL,
    buyer_name TEXT,

    -- Activation status
    active BOOLEAN NOT NULL DEFAULT false,

    -- One-time credential retrieval flag (CRITICAL SECURITY)
    -- Once true, shared_secret can NEVER be retrieved again
    credentials_retrieved BOOLEAN NOT NULL DEFAULT false,

    -- Shared secret for API authentication (generated on activation)
    -- This is the "crown jewel" - 32 bytes hex = 64 chars
    shared_secret CHAR(64),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at TIMESTAMPTZ,  -- When registration was requested
    activated_at TIMESTAMPTZ,    -- When owner clicked activation link
    credentials_retrieved_at TIMESTAMPTZ,  -- When agent retrieved credentials

    -- Metadata
    registration_ip INET,
    activation_ip INET,
    yacht_name TEXT,
    yacht_model TEXT,

    -- Audit trail
    last_seen_at TIMESTAMPTZ,
    api_calls_count BIGINT DEFAULT 0,

    -- Constraints
    CONSTRAINT valid_yacht_id CHECK (yacht_id ~ '^[A-Z0-9_-]+$'),
    CONSTRAINT valid_yacht_id_hash CHECK (yacht_id_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT valid_email CHECK (buyer_email ~ '^[^@]+@[^@]+\.[^@]+$'),
    CONSTRAINT valid_shared_secret CHECK (shared_secret IS NULL OR shared_secret ~ '^[a-f0-9]{64}$')
);

-- Add comments for documentation
COMMENT ON TABLE fleet_registry IS 'Central registry of all yachts with credentials. HIGHEST SECURITY.';
COMMENT ON COLUMN fleet_registry.shared_secret IS 'API auth secret - can only be retrieved ONCE via check-activation endpoint';
COMMENT ON COLUMN fleet_registry.credentials_retrieved IS 'Once true, shared_secret is never returned again';

-- ============================================================================
-- INDEXES
-- Optimized for the query patterns in n8n workflows
-- ============================================================================

-- Primary lookup: yacht_id + yacht_id_hash (used in registration)
CREATE INDEX IF NOT EXISTS idx_fleet_registry_lookup
    ON fleet_registry (yacht_id, yacht_id_hash);

-- Email lookup (for finding yachts by buyer)
CREATE INDEX IF NOT EXISTS idx_fleet_registry_email
    ON fleet_registry (buyer_email);

-- Active status filtering
CREATE INDEX IF NOT EXISTS idx_fleet_registry_active
    ON fleet_registry (active) WHERE active = true;

-- Cleanup query: inactive registrations older than X days
CREATE INDEX IF NOT EXISTS idx_fleet_registry_cleanup
    ON fleet_registry (active, registered_at)
    WHERE active = false AND registered_at IS NOT NULL;

-- ============================================================================
-- AUDIT LOG TABLE
-- Track all sensitive operations
-- ============================================================================

CREATE TABLE IF NOT EXISTS identity_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id TEXT REFERENCES fleet_registry(yacht_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_yacht
    ON identity_audit_log (yacht_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_action
    ON identity_audit_log (action, created_at DESC);

COMMENT ON TABLE identity_audit_log IS 'Audit trail for all identity operations';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to generate shared_secret on activation
CREATE OR REPLACE FUNCTION generate_shared_secret()
RETURNS TEXT AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to verify yacht_id_hash
CREATE OR REPLACE FUNCTION verify_yacht_hash(p_yacht_id TEXT, p_hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN encode(digest(p_yacht_id, 'sha256'), 'hex') = lower(p_hash);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to activate yacht (atomic operation)
CREATE OR REPLACE FUNCTION activate_yacht(p_yacht_id TEXT)
RETURNS TABLE(
    yacht_id TEXT,
    yacht_id_hash CHAR(64),
    shared_secret CHAR(64),
    activated_at TIMESTAMPTZ
) AS $$
DECLARE
    v_secret TEXT;
BEGIN
    -- Generate new secret
    v_secret := generate_shared_secret();

    -- Update and return in one atomic operation
    RETURN QUERY
    UPDATE fleet_registry
    SET
        active = true,
        activated_at = NOW(),
        shared_secret = v_secret
    WHERE fleet_registry.yacht_id = p_yacht_id
      AND fleet_registry.active = false
    RETURNING
        fleet_registry.yacht_id,
        fleet_registry.yacht_id_hash,
        fleet_registry.shared_secret,
        fleet_registry.activated_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to retrieve credentials (ONE TIME ONLY)
CREATE OR REPLACE FUNCTION retrieve_credentials(p_yacht_id TEXT)
RETURNS TABLE(
    status TEXT,
    yacht_id TEXT,
    yacht_id_hash CHAR(64),
    shared_secret CHAR(64),
    activated_at TIMESTAMPTZ,
    message TEXT
) AS $$
DECLARE
    v_record RECORD;
BEGIN
    -- Get current state
    SELECT * INTO v_record
    FROM fleet_registry fr
    WHERE fr.yacht_id = p_yacht_id;

    -- Check if yacht exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT
            'error'::TEXT,
            NULL::TEXT,
            NULL::CHAR(64),
            NULL::CHAR(64),
            NULL::TIMESTAMPTZ,
            'Yacht not found'::TEXT;
        RETURN;
    END IF;

    -- Check if not activated
    IF NOT v_record.active THEN
        RETURN QUERY SELECT
            'pending'::TEXT,
            v_record.yacht_id,
            NULL::CHAR(64),
            NULL::CHAR(64),
            NULL::TIMESTAMPTZ,
            'Waiting for owner activation'::TEXT;
        RETURN;
    END IF;

    -- Check if already retrieved
    IF v_record.credentials_retrieved THEN
        RETURN QUERY SELECT
            'already_retrieved'::TEXT,
            v_record.yacht_id,
            NULL::CHAR(64),
            NULL::CHAR(64),
            v_record.activated_at,
            'Credentials have already been retrieved'::TEXT;
        RETURN;
    END IF;

    -- Mark as retrieved and return credentials (ONE TIME ONLY)
    UPDATE fleet_registry
    SET
        credentials_retrieved = true,
        credentials_retrieved_at = NOW()
    WHERE fleet_registry.yacht_id = p_yacht_id;

    -- Log this critical action
    INSERT INTO identity_audit_log (yacht_id, action, details)
    VALUES (p_yacht_id, 'CREDENTIALS_RETRIEVED', jsonb_build_object(
        'timestamp', NOW(),
        'warning', 'ONE TIME RETRIEVAL - credentials will never be returned again'
    ));

    RETURN QUERY SELECT
        'active'::TEXT,
        v_record.yacht_id,
        v_record.yacht_id_hash,
        v_record.shared_secret,
        v_record.activated_at,
        'Credentials retrieved successfully'::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on fleet_registry
ALTER TABLE fleet_registry ENABLE ROW LEVEL SECURITY;

-- Enable RLS on audit log
ALTER TABLE identity_audit_log ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (for n8n workflows)
CREATE POLICY "Service role full access" ON fleet_registry
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON identity_audit_log
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Anon users cannot access fleet_registry at all
-- (No policy = no access)

-- ============================================================================
-- SEED DATA FOR TESTING (REMOVE IN PRODUCTION)
-- ============================================================================

-- Example yacht for testing (remove before production)
-- INSERT INTO fleet_registry (yacht_id, yacht_id_hash, buyer_email, yacht_name)
-- VALUES (
--     'MYSTIC_2025_001',
--     encode(digest('MYSTIC_2025_001', 'sha256'), 'hex'),
--     'buyer@example.com',
--     'M/Y Mystic'
-- );

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Revoke all from public
REVOKE ALL ON fleet_registry FROM PUBLIC;
REVOKE ALL ON identity_audit_log FROM PUBLIC;

-- Grant to authenticated role (if needed for future use)
-- GRANT SELECT ON fleet_registry TO authenticated;

-- Grant execute on functions to service_role only
REVOKE ALL ON FUNCTION generate_shared_secret() FROM PUBLIC;
REVOKE ALL ON FUNCTION verify_yacht_hash(TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION activate_yacht(TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION retrieve_credentials(TEXT) FROM PUBLIC;

-- ============================================================================
-- END OF IDENTITY SCHEMA
-- ============================================================================
