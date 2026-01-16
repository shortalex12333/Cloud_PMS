-- ============================================================================
-- Migration: Create pms_checklists table
-- Description: Master checklist templates for work orders, equipment, safety
-- Author: Claude
-- Date: 2026-01-16
-- ============================================================================

-- Create pms_checklists table
CREATE TABLE IF NOT EXISTS pms_checklists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Core fields
    name VARCHAR(255) NOT NULL,
    description TEXT,
    checklist_type VARCHAR(50) NOT NULL DEFAULT 'maintenance',
    -- Types: maintenance, safety, inspection, departure, arrival, watch, custom

    -- Associations (optional - checklist can be standalone template)
    equipment_id UUID,
    work_order_id UUID,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    -- Status: active, archived, draft
    is_template BOOLEAN NOT NULL DEFAULT false,

    -- Completion tracking
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,

    -- Metadata for extensibility
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
    CONSTRAINT fk_pms_checklists_equipment
        FOREIGN KEY (equipment_id) REFERENCES pms_equipment(id) ON DELETE SET NULL,
    CONSTRAINT fk_pms_checklists_work_order
        FOREIGN KEY (work_order_id) REFERENCES pms_work_orders(id) ON DELETE SET NULL,

    -- Check constraints
    CONSTRAINT chk_pms_checklists_type
        CHECK (checklist_type IN ('maintenance', 'safety', 'inspection', 'departure', 'arrival', 'watch', 'custom')),
    CONSTRAINT chk_pms_checklists_status
        CHECK (status IN ('active', 'archived', 'draft'))
);

-- Comment on table
COMMENT ON TABLE pms_checklists IS 'Master checklist templates and instances for maintenance, safety, and inspections';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_checklists_yacht_id ON pms_checklists(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_checklists_work_order_id ON pms_checklists(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_checklists_equipment_id ON pms_checklists(equipment_id) WHERE equipment_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_checklists_type ON pms_checklists(checklist_type);
CREATE INDEX IF NOT EXISTS idx_pms_checklists_status ON pms_checklists(status) WHERE deleted_at IS NULL;

-- Enable Row Level Security
ALTER TABLE pms_checklists ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON pms_checklists
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policy: Users can only access checklists for yachts they have access to
-- Note: Assumes user_yacht_access table exists or use direct JWT claim
CREATE POLICY yacht_isolation_select ON pms_checklists
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_checklists.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_checklists
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_checklists.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON pms_checklists
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_checklists.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_checklists
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_checklists.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_pms_checklists_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_checklists_updated_at ON pms_checklists;
CREATE TRIGGER trg_pms_checklists_updated_at
    BEFORE UPDATE ON pms_checklists
    FOR EACH ROW
    EXECUTE FUNCTION update_pms_checklists_updated_at();
