-- ============================================================================
-- MASTER DB: Idempotency Records Table
-- Phase 2: Router Hardening - Idempotency Layer
-- ============================================================================
--
-- Purpose:
--   Track idempotency keys for MUTATE/SIGNED/ADMIN actions.
--   Ensures repeated requests return identical responses without side effects.
--
-- Security invariants:
--   - Keys scoped to yacht_id (no cross-tenant key collisions)
--   - Request hash prevents replay attacks with different payloads
--   - TTL-based expiry (24 hours default)
--   - No sensitive data in response_summary
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS idempotency_records (
    -- Primary key is the idempotency key itself (unique per yacht)
    idempotency_key TEXT NOT NULL,
    yacht_id UUID NOT NULL,

    -- Action context
    action_id TEXT NOT NULL,
    user_id UUID NOT NULL,

    -- Request fingerprint (prevents different payloads with same key)
    request_hash TEXT NOT NULL,

    -- Response (safe summary only, no sensitive data)
    response_status INTEGER,           -- HTTP status code
    response_summary JSONB,            -- Safe subset of response
    response_hash TEXT,                -- Hash of full response for verification

    -- Lifecycle
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '24 hours',
    completed_at TIMESTAMPTZ,          -- NULL until action completes

    -- Composite primary key: key + yacht for isolation
    PRIMARY KEY (idempotency_key, yacht_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_records(expires_at);
CREATE INDEX IF NOT EXISTS idx_idempotency_user ON idempotency_records(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_idempotency_yacht_action ON idempotency_records(yacht_id, action_id);

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE idempotency_records ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (backend operations)
CREATE POLICY idempotency_service_all ON idempotency_records
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- Cleanup Function (run periodically)
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_idempotency_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM idempotency_records
        WHERE expires_at < now()
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Check for existing idempotent request
CREATE OR REPLACE FUNCTION check_idempotency(
    p_key TEXT,
    p_yacht_id UUID,
    p_action_id TEXT,
    p_request_hash TEXT
)
RETURNS TABLE (
    found BOOLEAN,
    completed BOOLEAN,
    response_status INTEGER,
    response_summary JSONB,
    hash_mismatch BOOLEAN
) AS $$
DECLARE
    v_record idempotency_records%ROWTYPE;
BEGIN
    SELECT * INTO v_record
    FROM idempotency_records
    WHERE idempotency_key = p_key
      AND yacht_id = p_yacht_id
      AND expires_at > now();

    IF NOT FOUND THEN
        RETURN QUERY SELECT false, false, NULL::INTEGER, NULL::JSONB, false;
        RETURN;
    END IF;

    -- Check if request hash matches (different payload = error)
    IF v_record.request_hash != p_request_hash THEN
        RETURN QUERY SELECT true, false, NULL::INTEGER, NULL::JSONB, true;
        RETURN;
    END IF;

    -- Return existing response if completed
    RETURN QUERY SELECT
        true,
        v_record.completed_at IS NOT NULL,
        v_record.response_status,
        v_record.response_summary,
        false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create idempotency record (called at request start)
CREATE OR REPLACE FUNCTION create_idempotency_record(
    p_key TEXT,
    p_yacht_id UUID,
    p_action_id TEXT,
    p_user_id UUID,
    p_request_hash TEXT,
    p_ttl_hours INTEGER DEFAULT 24
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO idempotency_records (
        idempotency_key,
        yacht_id,
        action_id,
        user_id,
        request_hash,
        expires_at
    ) VALUES (
        p_key,
        p_yacht_id,
        p_action_id,
        p_user_id,
        p_request_hash,
        now() + (p_ttl_hours || ' hours')::INTERVAL
    )
    ON CONFLICT (idempotency_key, yacht_id) DO NOTHING;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Complete idempotency record (called after action succeeds)
CREATE OR REPLACE FUNCTION complete_idempotency_record(
    p_key TEXT,
    p_yacht_id UUID,
    p_status INTEGER,
    p_summary JSONB,
    p_response_hash TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE idempotency_records
    SET response_status = p_status,
        response_summary = p_summary,
        response_hash = p_response_hash,
        completed_at = now()
    WHERE idempotency_key = p_key
      AND yacht_id = p_yacht_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE idempotency_records IS 'Idempotency tracking for MUTATE/SIGNED/ADMIN actions. Scoped to yacht_id. TTL 24h default.';
