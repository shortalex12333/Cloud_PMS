-- =============================================================================
-- MIGRATION: Two-Phase Mutation Infrastructure
-- =============================================================================
--
-- Purpose: Support prepare→commit flows with idempotency tokens
--
-- Usage:
-- 1. Client calls prepare endpoint → gets idempotency_token + preview
-- 2. Client reviews preview (storage paths, confirmation dialogs)
-- 3. Client calls commit endpoint with token → mutation applied
--
-- Benefits:
-- - Idempotent retries (same token = same result)
-- - Preview before commit (storage confirmation)
-- - Timeout protection (expires_at)
-- - Audit trail for staged mutations
--
-- =============================================================================

-- Staged Mutations Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS pms_staged_mutations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Idempotency token (unique per mutation request)
    idempotency_token text NOT NULL UNIQUE,

    -- Context
    yacht_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action_id text NOT NULL,

    -- Preview data
    preview_hash text NOT NULL,  -- SHA256 of payload for validation
    payload jsonb NOT NULL,       -- Full mutation payload
    preview_data jsonb,           -- Rendered preview (storage paths, etc.)

    -- Lifecycle
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'committed', 'expired', 'cancelled')),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone NOT NULL,
    committed_at timestamp with time zone,

    -- Audit
    commit_result jsonb,          -- Result of commit operation
    commit_error text             -- Error message if commit failed
);

COMMENT ON TABLE pms_staged_mutations IS 'Two-phase mutation staging for prepare→commit flows';
COMMENT ON COLUMN pms_staged_mutations.idempotency_token IS 'Unique token for idempotent commit';
COMMENT ON COLUMN pms_staged_mutations.preview_hash IS 'SHA256 of payload for validation at commit time';
COMMENT ON COLUMN pms_staged_mutations.preview_data IS 'Rendered preview (storage paths, confirmation details)';
COMMENT ON COLUMN pms_staged_mutations.expires_at IS 'Token expiry time (default: 15 minutes from creation)';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_staged_mutations_token ON pms_staged_mutations (idempotency_token);
CREATE INDEX IF NOT EXISTS idx_staged_mutations_yacht_user ON pms_staged_mutations (yacht_id, user_id);
CREATE INDEX IF NOT EXISTS idx_staged_mutations_expires ON pms_staged_mutations (expires_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_staged_mutations_action ON pms_staged_mutations (action_id, status);

-- RLS Policies
-- =============================================================================

ALTER TABLE pms_staged_mutations ENABLE ROW LEVEL SECURITY;

-- Users can only see their own staged mutations
CREATE POLICY "user_scoped_staged_mutations" ON pms_staged_mutations
    FOR SELECT TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND user_id = auth.uid()
    );

-- Users can insert their own staged mutations
CREATE POLICY "user_insert_staged_mutations" ON pms_staged_mutations
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND user_id = auth.uid()
    );

-- Users can update their own pending mutations (to commit/cancel)
CREATE POLICY "user_update_staged_mutations" ON pms_staged_mutations
    FOR UPDATE TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND user_id = auth.uid()
        AND status = 'pending'
    )
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND user_id = auth.uid()
    );

-- Service role can manage all mutations (for cleanup jobs)
CREATE POLICY "service_role_manage_staged_mutations" ON pms_staged_mutations
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Helper Functions
-- =============================================================================

-- Create a staged mutation (prepare phase)
CREATE OR REPLACE FUNCTION stage_mutation(
    p_yacht_id uuid,
    p_user_id uuid,
    p_action_id text,
    p_payload jsonb,
    p_preview_data jsonb DEFAULT NULL,
    p_expires_minutes integer DEFAULT 15
)
RETURNS TABLE (
    idempotency_token text,
    preview_hash text,
    expires_at timestamp with time zone
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_token text;
    v_hash text;
    v_expires timestamp with time zone;
BEGIN
    -- Generate unique token
    v_token := encode(gen_random_bytes(32), 'hex');

    -- Compute payload hash
    v_hash := encode(digest(p_payload::text, 'sha256'), 'hex');

    -- Set expiry
    v_expires := now() + (p_expires_minutes || ' minutes')::interval;

    -- Insert staged mutation
    INSERT INTO pms_staged_mutations (
        idempotency_token,
        yacht_id,
        user_id,
        action_id,
        preview_hash,
        payload,
        preview_data,
        expires_at
    ) VALUES (
        v_token,
        p_yacht_id,
        p_user_id,
        p_action_id,
        v_hash,
        p_payload,
        p_preview_data,
        v_expires
    );

    RETURN QUERY SELECT v_token, v_hash, v_expires;
END;
$$;

COMMENT ON FUNCTION stage_mutation IS 'Create a staged mutation for two-phase commit flow';

-- Commit a staged mutation
CREATE OR REPLACE FUNCTION commit_mutation(
    p_token text,
    p_hash text,
    p_user_id uuid
)
RETURNS TABLE (
    success boolean,
    payload jsonb,
    error_message text
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_mutation pms_staged_mutations%ROWTYPE;
BEGIN
    -- Fetch the staged mutation
    SELECT * INTO v_mutation
    FROM pms_staged_mutations
    WHERE idempotency_token = p_token
      AND user_id = p_user_id
    FOR UPDATE;

    -- Check if mutation exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT false, NULL::jsonb, 'Mutation not found or access denied';
        RETURN;
    END IF;

    -- Check if already committed (idempotent)
    IF v_mutation.status = 'committed' THEN
        RETURN QUERY SELECT true, v_mutation.payload, NULL::text;
        RETURN;
    END IF;

    -- Check if expired
    IF v_mutation.status = 'expired' OR v_mutation.expires_at < now() THEN
        UPDATE pms_staged_mutations SET status = 'expired' WHERE id = v_mutation.id;
        RETURN QUERY SELECT false, NULL::jsonb, 'Mutation has expired';
        RETURN;
    END IF;

    -- Check if cancelled
    IF v_mutation.status = 'cancelled' THEN
        RETURN QUERY SELECT false, NULL::jsonb, 'Mutation was cancelled';
        RETURN;
    END IF;

    -- Validate hash
    IF v_mutation.preview_hash != p_hash THEN
        RETURN QUERY SELECT false, NULL::jsonb, 'Payload hash mismatch';
        RETURN;
    END IF;

    -- Mark as committed
    UPDATE pms_staged_mutations
    SET status = 'committed', committed_at = now()
    WHERE id = v_mutation.id;

    -- Return payload for execution
    RETURN QUERY SELECT true, v_mutation.payload, NULL::text;
END;
$$;

COMMENT ON FUNCTION commit_mutation IS 'Commit a staged mutation (validates token and hash)';

-- Cleanup expired mutations (run periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_mutations()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count integer;
BEGIN
    UPDATE pms_staged_mutations
    SET status = 'expired'
    WHERE status = 'pending'
      AND expires_at < now();

    GET DIAGNOSTICS v_count = ROW_COUNT;

    -- Delete very old mutations (> 7 days)
    DELETE FROM pms_staged_mutations
    WHERE created_at < now() - interval '7 days'
      AND status IN ('expired', 'committed', 'cancelled');

    RETURN v_count;
END;
$$;

COMMENT ON FUNCTION cleanup_expired_mutations IS 'Mark expired mutations and clean up old records';

-- =============================================================================
-- End of Migration
-- =============================================================================
