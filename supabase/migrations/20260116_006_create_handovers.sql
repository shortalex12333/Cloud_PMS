-- ============================================================================
-- Migration: Create handovers table
-- Description: Master handover records for shift/watch handovers
-- Author: Claude
-- Date: 2026-01-16
-- ============================================================================

-- Create handovers table
CREATE TABLE IF NOT EXISTS handovers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Handover details
    title VARCHAR(255),
    description TEXT,

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- Status: draft, pending_review, approved, completed, cancelled

    -- Assignment/Shift info
    from_user_id UUID,
    to_user_id UUID,
    shift_date DATE,
    shift_type VARCHAR(50),  -- day, night, watch_1, watch_2, etc.

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Approval
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,

    -- Check constraints
    CONSTRAINT chk_handovers_status
        CHECK (status IN ('draft', 'pending_review', 'approved', 'completed', 'cancelled'))
);

-- Comment on table
COMMENT ON TABLE handovers IS 'Master handover records for shift/watch handovers between crew members';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_handovers_yacht_id ON handovers(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handovers_status ON handovers(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_handovers_from_user ON handovers(from_user_id) WHERE from_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_handovers_to_user ON handovers(to_user_id) WHERE to_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_handovers_shift_date ON handovers(shift_date) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_handovers_created_at ON handovers(created_at DESC);

-- Enable Row Level Security
ALTER TABLE handovers ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON handovers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policies for authenticated users
CREATE POLICY yacht_isolation_select ON handovers
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handovers.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON handovers
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handovers.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON handovers
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handovers.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON handovers
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handovers.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_handovers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_handovers_updated_at ON handovers;
CREATE TRIGGER trg_handovers_updated_at
    BEFORE UPDATE ON handovers
    FOR EACH ROW
    EXECUTE FUNCTION update_handovers_updated_at();

-- Trigger to set completed_at when status changes to completed
CREATE OR REPLACE FUNCTION set_handover_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_handover_completed ON handovers;
CREATE TRIGGER trg_set_handover_completed
    BEFORE UPDATE ON handovers
    FOR EACH ROW
    EXECUTE FUNCTION set_handover_completed_at();
