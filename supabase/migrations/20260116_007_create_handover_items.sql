-- ============================================================================
-- Migration: Create handover_items table
-- Description: Individual items within a handover (faults, work orders, equipment, etc.)
-- Author: Claude
-- Date: 2026-01-16
-- Depends on: handovers
-- ============================================================================

-- Create handover_items table
CREATE TABLE IF NOT EXISTS handover_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    handover_id UUID NOT NULL,

    -- Entity reference (polymorphic)
    entity_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    -- Types: fault, work_order, equipment, part, document, note

    -- Item details
    section VARCHAR(100),  -- Section in handover (e.g., "Outstanding Issues", "Completed Tasks")
    summary TEXT,
    priority INTEGER DEFAULT 0,

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Status: pending, acknowledged, completed, deferred

    -- Acknowledgement
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    acknowledgement_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    added_by UUID NOT NULL,  -- User who added this item
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,

    -- Foreign keys
    CONSTRAINT fk_handover_items_handover
        FOREIGN KEY (handover_id) REFERENCES handovers(id) ON DELETE CASCADE,

    -- Check constraints
    CONSTRAINT chk_handover_items_entity_type
        CHECK (entity_type IN ('fault', 'work_order', 'equipment', 'part', 'document', 'note', 'general')),
    CONSTRAINT chk_handover_items_status
        CHECK (status IN ('pending', 'acknowledged', 'completed', 'deferred')),

    -- Unique constraint: prevent duplicate entity in same handover
    CONSTRAINT uq_handover_items_entity
        UNIQUE (handover_id, entity_id, entity_type, deleted_at)
);

-- Comment on table
COMMENT ON TABLE handover_items IS 'Individual items within a handover linking to various entities';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_handover_items_yacht_id ON handover_items(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_handover_id ON handover_items(handover_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_entity ON handover_items(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_status ON handover_items(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_handover_items_section ON handover_items(section) WHERE section IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_handover_items_added_by ON handover_items(added_by);

-- Enable Row Level Security
ALTER TABLE handover_items ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON handover_items
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policies for authenticated users
CREATE POLICY yacht_isolation_select ON handover_items
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handover_items.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON handover_items
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handover_items.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON handover_items
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handover_items.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON handover_items
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = handover_items.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_handover_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_handover_items_updated_at ON handover_items;
CREATE TRIGGER trg_handover_items_updated_at
    BEFORE UPDATE ON handover_items
    FOR EACH ROW
    EXECUTE FUNCTION update_handover_items_updated_at();

-- Trigger to set acknowledged_at when status changes
CREATE OR REPLACE FUNCTION set_handover_item_acknowledged()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'acknowledged' AND OLD.status != 'acknowledged' THEN
        NEW.acknowledged_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_handover_item_acknowledged ON handover_items;
CREATE TRIGGER trg_set_handover_item_acknowledged
    BEFORE UPDATE ON handover_items
    FOR EACH ROW
    EXECUTE FUNCTION set_handover_item_acknowledged();
