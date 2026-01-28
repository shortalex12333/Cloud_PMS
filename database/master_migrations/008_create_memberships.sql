-- ============================================================================
-- MASTER DB: Memberships Table
-- Phase 1: Access Lifecycle Implementation
-- ============================================================================
--
-- Purpose:
--   Canonical membership tracking for user-to-yacht assignments.
--   Replaces ad-hoc user_accounts.status with explicit lifecycle states.
--
-- Security invariants:
--   - Server-resolved context: membership status checked on every request
--   - Deny-by-default: only ACTIVE memberships allow API access
--   - Audit trail: all state changes logged to security_events
--   - Bounded revocation: REVOKED takes effect within TTL (< 2 min)
--
-- Status transitions:
--   INVITED -> ACCEPTED -> PROVISIONED -> ACTIVE
--   ACTIVE -> SUSPENDED -> ACTIVE (reinstatement)
--   ANY -> REVOKED (terminal, no return)
--
-- ============================================================================

-- Create enum for membership statuses
DO $$ BEGIN
    CREATE TYPE membership_status AS ENUM (
        'INVITED',      -- Initial invite sent, awaiting acceptance
        'ACCEPTED',     -- User accepted invite, awaiting provisioning
        'PROVISIONED',  -- TENANT records created, awaiting activation
        'ACTIVE',       -- Full access granted
        'SUSPENDED',    -- Temporary access removal (can be reinstated)
        'REVOKED'       -- Permanent access removal (terminal state)
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create memberships table
CREATE TABLE IF NOT EXISTS memberships (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core identity (unique constraint below)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL,  -- References fleet_registry.yacht_id

    -- Lifecycle state
    status membership_status NOT NULL DEFAULT 'INVITED',

    -- Approval chain (2-person rule for privileged roles)
    invited_by UUID REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),
    approved_at TIMESTAMPTZ,

    -- Time bounds
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_until TIMESTAMPTZ,  -- NULL = no expiry

    -- Metadata
    role_requested TEXT,  -- Role requested at invite time
    notes TEXT,           -- Admin notes (not exposed to user)

    -- Idempotency
    idempotency_key TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Unique: one membership per user per yacht
    CONSTRAINT memberships_user_yacht_unique UNIQUE (user_id, yacht_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_memberships_user_id ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_yacht_id ON memberships(yacht_id);
CREATE INDEX IF NOT EXISTS idx_memberships_status ON memberships(status);
CREATE INDEX IF NOT EXISTS idx_memberships_user_status ON memberships(user_id, status);
CREATE INDEX IF NOT EXISTS idx_memberships_yacht_status ON memberships(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_memberships_idempotency ON memberships(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_memberships_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_memberships_updated_at ON memberships;
CREATE TRIGGER trigger_memberships_updated_at
    BEFORE UPDATE ON memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_memberships_updated_at();

-- ============================================================================
-- RLS Policies (MASTER DB - admin access only)
-- ============================================================================

ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (backend operations)
CREATE POLICY memberships_service_all ON memberships
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Users can view their own memberships
CREATE POLICY memberships_user_select ON memberships
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Get active membership for user
CREATE OR REPLACE FUNCTION get_active_membership(p_user_id UUID)
RETURNS TABLE (
    membership_id UUID,
    yacht_id UUID,
    status membership_status,
    valid_until TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.yacht_id,
        m.status,
        m.valid_until
    FROM memberships m
    WHERE m.user_id = p_user_id
      AND m.status = 'ACTIVE'
      AND (m.valid_until IS NULL OR m.valid_until > now())
    ORDER BY m.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if user has active membership for specific yacht
CREATE OR REPLACE FUNCTION has_active_membership(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM memberships
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND status = 'ACTIVE'
          AND (valid_until IS NULL OR valid_until > now())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Audit trigger for security_events
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_membership_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_event_type TEXT;
    v_old_values JSONB;
    v_new_values JSONB;
BEGIN
    -- Determine event type
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'membership_created';
        v_old_values := NULL;
        v_new_values := jsonb_build_object(
            'membership_id', NEW.id,
            'user_id', NEW.user_id,
            'yacht_id', NEW.yacht_id,
            'status', NEW.status,
            'invited_by', NEW.invited_by
        );
    ELSIF TG_OP = 'UPDATE' THEN
        v_event_type := 'membership_updated';
        -- Only log if status changed
        IF OLD.status != NEW.status THEN
            v_event_type := 'membership_status_change';
        END IF;
        v_old_values := jsonb_build_object(
            'status', OLD.status,
            'valid_until', OLD.valid_until
        );
        v_new_values := jsonb_build_object(
            'status', NEW.status,
            'valid_until', NEW.valid_until,
            'approved_by', NEW.approved_by
        );
    ELSIF TG_OP = 'DELETE' THEN
        v_event_type := 'membership_deleted';
        v_old_values := jsonb_build_object(
            'membership_id', OLD.id,
            'user_id', OLD.user_id,
            'yacht_id', OLD.yacht_id,
            'status', OLD.status
        );
        v_new_values := NULL;
    END IF;

    -- Insert audit record
    INSERT INTO security_events (
        event_type,
        user_id,
        yacht_id,
        details,
        created_at
    ) VALUES (
        v_event_type,
        COALESCE(NEW.user_id, OLD.user_id),
        COALESCE(NEW.yacht_id, OLD.yacht_id),
        jsonb_build_object(
            'old_values', v_old_values,
            'new_values', v_new_values,
            'triggered_by', current_setting('request.jwt.claims', true)::jsonb->>'sub'
        ),
        now()
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trigger_audit_membership_changes ON memberships;
CREATE TRIGGER trigger_audit_membership_changes
    AFTER INSERT OR UPDATE OR DELETE ON memberships
    FOR EACH ROW
    EXECUTE FUNCTION audit_membership_changes();

-- ============================================================================
-- Migration from user_accounts (if needed)
-- ============================================================================
--
-- To migrate existing user_accounts to memberships:
--
-- INSERT INTO memberships (user_id, yacht_id, status, created_at)
-- SELECT id, yacht_id,
--        CASE WHEN status = 'active' THEN 'ACTIVE'::membership_status
--             WHEN status = 'pending' THEN 'INVITED'::membership_status
--             ELSE 'SUSPENDED'::membership_status
--        END,
--        created_at
-- FROM user_accounts
-- WHERE yacht_id IS NOT NULL
-- ON CONFLICT (user_id, yacht_id) DO NOTHING;
--
-- ============================================================================

COMMENT ON TABLE memberships IS 'Canonical user-to-yacht membership with explicit lifecycle states. Server-resolved context for all API access.';
COMMENT ON COLUMN memberships.status IS 'Lifecycle state: INVITED->ACCEPTED->PROVISIONED->ACTIVE; SUSPENDED is temporary; REVOKED is terminal.';
COMMENT ON COLUMN memberships.approved_by IS '2-person rule: privileged roles require different approver than inviter.';
