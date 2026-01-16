-- ============================================================================
-- Migration: Create pms_work_order_checklist table
-- Description: Checklist items specific to individual work orders
-- Author: Claude
-- Date: 2026-01-16
-- Depends on: pms_work_orders
-- ============================================================================

-- Create pms_work_order_checklist table
CREATE TABLE IF NOT EXISTS pms_work_order_checklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    work_order_id UUID NOT NULL,

    -- Checklist item content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    instructions TEXT,
    sequence INTEGER NOT NULL DEFAULT 0,

    -- Completion tracking
    is_completed BOOLEAN NOT NULL DEFAULT false,
    completed_at TIMESTAMPTZ,
    completed_by UUID,
    completion_notes TEXT,

    -- Requirements
    is_required BOOLEAN NOT NULL DEFAULT true,
    requires_photo BOOLEAN NOT NULL DEFAULT false,
    requires_signature BOOLEAN NOT NULL DEFAULT false,

    -- Photo/signature if required
    photo_url TEXT,
    signature_data JSONB,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,

    -- Foreign keys
    CONSTRAINT fk_pms_wo_checklist_work_order
        FOREIGN KEY (work_order_id) REFERENCES pms_work_orders(id) ON DELETE CASCADE
);

-- Comment on table
COMMENT ON TABLE pms_work_order_checklist IS 'Checklist items for individual work orders with completion tracking';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_wo_checklist_yacht_id ON pms_work_order_checklist(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_wo_checklist_work_order_id ON pms_work_order_checklist(work_order_id);
CREATE INDEX IF NOT EXISTS idx_pms_wo_checklist_sequence ON pms_work_order_checklist(work_order_id, sequence);
CREATE INDEX IF NOT EXISTS idx_pms_wo_checklist_completed ON pms_work_order_checklist(is_completed) WHERE deleted_at IS NULL;

-- Enable Row Level Security
ALTER TABLE pms_work_order_checklist ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON pms_work_order_checklist
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policies for authenticated users
CREATE POLICY yacht_isolation_select ON pms_work_order_checklist
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_work_order_checklist.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_work_order_checklist
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_work_order_checklist.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON pms_work_order_checklist
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_work_order_checklist.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_work_order_checklist
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_work_order_checklist.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_pms_wo_checklist_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_wo_checklist_updated_at ON pms_work_order_checklist;
CREATE TRIGGER trg_pms_wo_checklist_updated_at
    BEFORE UPDATE ON pms_work_order_checklist
    FOR EACH ROW
    EXECUTE FUNCTION update_pms_wo_checklist_updated_at();

-- Trigger to set completed_at when is_completed changes to true
CREATE OR REPLACE FUNCTION set_wo_checklist_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_completed = true AND (OLD.is_completed = false OR OLD.is_completed IS NULL) THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_wo_checklist_completed ON pms_work_order_checklist;
CREATE TRIGGER trg_set_wo_checklist_completed
    BEFORE UPDATE ON pms_work_order_checklist
    FOR EACH ROW
    EXECUTE FUNCTION set_wo_checklist_completed_at();
