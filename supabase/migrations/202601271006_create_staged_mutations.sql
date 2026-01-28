-- Migration: Create pms_staged_mutations table for two-phase mutations
-- Part of: Fault Lens Entity Extraction & Prefill
-- Branch: fault/entity-extraction-prefill_v1

-- Purpose: Cache mutation previews between prepare and commit phases
-- TTL: 5-15 minutes (expired rows cleaned by cron or on-access)

BEGIN;

-- ============================================================================
-- TABLE: pms_staged_mutations
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_staged_mutations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Idempotency token (returned to frontend, used to commit)
    idempotency_token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- Action context
    action_id TEXT NOT NULL,
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    entity_id UUID,  -- Optional: the entity being mutated (fault_id, etc.)
    entity_type TEXT,  -- 'fault', 'work_order', etc.

    -- Preview data
    preview_hash TEXT NOT NULL,  -- SHA256 of payload_snapshot for validation
    payload_snapshot JSONB NOT NULL DEFAULT '{}',  -- Minimal prefill data
    proposed_payload JSONB NOT NULL DEFAULT '{}',  -- Full proposed payload
    unresolved_fields TEXT[] DEFAULT '{}',  -- Fields needing user input
    warnings TEXT[] DEFAULT '{}',  -- Warnings shown in preview

    -- Metadata
    requires_signature BOOLEAN NOT NULL DEFAULT false,
    signature_role TEXT,  -- Expected role for signing

    -- TTL
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,  -- Set when commit succeeds

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- Note: yacht_id not FK constrained (consistent with other PMS tables)
);

-- Index for lookup by token
CREATE INDEX IF NOT EXISTS idx_staged_mutations_token
ON pms_staged_mutations(idempotency_token)
WHERE consumed_at IS NULL;

-- Index for cleanup of expired rows
CREATE INDEX IF NOT EXISTS idx_staged_mutations_expires
ON pms_staged_mutations(expires_at)
WHERE consumed_at IS NULL;

-- Index for user lookup
CREATE INDEX IF NOT EXISTS idx_staged_mutations_user
ON pms_staged_mutations(user_id, yacht_id)
WHERE consumed_at IS NULL;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_staged_mutations ENABLE ROW LEVEL SECURITY;

-- Users can only see their own staged mutations
CREATE POLICY "user_own_staged_mutations_select"
ON pms_staged_mutations FOR SELECT TO authenticated
USING (
    user_id = auth.uid()
    AND yacht_id = public.get_user_yacht_id()
);

-- Users can insert their own staged mutations
CREATE POLICY "user_own_staged_mutations_insert"
ON pms_staged_mutations FOR INSERT TO authenticated
WITH CHECK (
    user_id = auth.uid()
    AND yacht_id = public.get_user_yacht_id()
);

-- Users can update their own staged mutations (to mark consumed)
CREATE POLICY "user_own_staged_mutations_update"
ON pms_staged_mutations FOR UPDATE TO authenticated
USING (
    user_id = auth.uid()
    AND yacht_id = public.get_user_yacht_id()
)
WITH CHECK (
    user_id = auth.uid()
    AND yacht_id = public.get_user_yacht_id()
);

-- Users can delete their own staged mutations
CREATE POLICY "user_own_staged_mutations_delete"
ON pms_staged_mutations FOR DELETE TO authenticated
USING (
    user_id = auth.uid()
    AND yacht_id = public.get_user_yacht_id()
);

-- ============================================================================
-- CLEANUP FUNCTION (optional - can also be done in application)
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_staged_mutations()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM pms_staged_mutations
    WHERE expires_at < NOW()
    OR consumed_at IS NOT NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Grant execute to authenticated users (for on-access cleanup)
GRANT EXECUTE ON FUNCTION cleanup_expired_staged_mutations() TO authenticated;

COMMIT;

-- ============================================================================
-- USAGE NOTES
-- ============================================================================
--
-- Prepare Phase:
--   INSERT INTO pms_staged_mutations (
--       action_id, user_id, yacht_id, entity_id, entity_type,
--       preview_hash, payload_snapshot, proposed_payload,
--       unresolved_fields, warnings, requires_signature, signature_role,
--       expires_at
--   ) VALUES (
--       'create_work_order_from_fault', auth.uid(), get_user_yacht_id(),
--       :fault_id, 'fault',
--       :hash, :snapshot, :proposed,
--       ARRAY['assigned_to'], ARRAY['Fault already has WO'],
--       true, 'captain',
--       NOW() + INTERVAL '10 minutes'
--   )
--   RETURNING idempotency_token;
--
-- Commit Phase:
--   SELECT * FROM pms_staged_mutations
--   WHERE idempotency_token = :token
--     AND user_id = auth.uid()
--     AND consumed_at IS NULL
--     AND expires_at > NOW();
--
--   -- Validate preview_hash matches
--   -- Execute mutation
--   -- Mark consumed:
--   UPDATE pms_staged_mutations SET consumed_at = NOW()
--   WHERE idempotency_token = :token;
