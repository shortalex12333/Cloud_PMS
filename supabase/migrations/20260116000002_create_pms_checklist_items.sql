-- ============================================================================
-- Migration: Create pms_checklist_items table
-- Description: Individual items within a checklist
-- Author: Claude
-- Date: 2026-01-16
-- Depends on: pms_checklists
-- ============================================================================

-- Create pms_checklist_items table
CREATE TABLE IF NOT EXISTS pms_checklist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    checklist_id UUID NOT NULL,

    -- Item content
    description TEXT NOT NULL,
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
    requires_value BOOLEAN NOT NULL DEFAULT false,
    value_type VARCHAR(20),  -- number, text, boolean, date
    value_unit VARCHAR(50),  -- mm, psi, hours, etc.
    value_min NUMERIC,
    value_max NUMERIC,

    -- Recorded value (if requires_value)
    recorded_value TEXT,
    recorded_at TIMESTAMPTZ,
    recorded_by UUID,

    -- Photo/signature if required
    photo_url TEXT,
    signature_data JSONB,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Status: pending, in_progress, completed, skipped, na

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
    CONSTRAINT fk_pms_checklist_items_checklist
        FOREIGN KEY (checklist_id) REFERENCES pms_checklists(id) ON DELETE CASCADE,

    -- Check constraints
    CONSTRAINT chk_pms_checklist_items_status
        CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped', 'na')),
    CONSTRAINT chk_pms_checklist_items_value_type
        CHECK (value_type IS NULL OR value_type IN ('number', 'text', 'boolean', 'date'))
);

-- Comment on table
COMMENT ON TABLE pms_checklist_items IS 'Individual checklist items with completion tracking and value recording';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_checklist_items_yacht_id ON pms_checklist_items(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_checklist_items_checklist_id ON pms_checklist_items(checklist_id);
CREATE INDEX IF NOT EXISTS idx_pms_checklist_items_sequence ON pms_checklist_items(checklist_id, sequence);
CREATE INDEX IF NOT EXISTS idx_pms_checklist_items_status ON pms_checklist_items(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_pms_checklist_items_completed ON pms_checklist_items(is_completed) WHERE deleted_at IS NULL;

-- Enable Row Level Security
ALTER TABLE pms_checklist_items ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON pms_checklist_items
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policy: Users can only access items for their yacht
CREATE POLICY yacht_isolation_select ON pms_checklist_items
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY yacht_isolation_insert ON pms_checklist_items
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY yacht_isolation_update ON pms_checklist_items
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY yacht_isolation_delete ON pms_checklist_items
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_pms_checklist_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_checklist_items_updated_at ON pms_checklist_items;
CREATE TRIGGER trg_pms_checklist_items_updated_at
    BEFORE UPDATE ON pms_checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION update_pms_checklist_items_updated_at();

-- Trigger to update parent checklist completion count
CREATE OR REPLACE FUNCTION update_checklist_completion_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE pms_checklists
    SET
        completed_items = (
            SELECT COUNT(*) FROM pms_checklist_items
            WHERE checklist_id = COALESCE(NEW.checklist_id, OLD.checklist_id)
            AND is_completed = true
            AND deleted_at IS NULL
        ),
        total_items = (
            SELECT COUNT(*) FROM pms_checklist_items
            WHERE checklist_id = COALESCE(NEW.checklist_id, OLD.checklist_id)
            AND deleted_at IS NULL
        ),
        updated_at = NOW()
    WHERE id = COALESCE(NEW.checklist_id, OLD.checklist_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_checklist_counts ON pms_checklist_items;
CREATE TRIGGER trg_update_checklist_counts
    AFTER INSERT OR UPDATE OR DELETE ON pms_checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION update_checklist_completion_count();
