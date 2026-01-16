-- ============================================================================
-- Migration: Create pms_attachments table
-- Description: File attachments (photos, documents) for faults, work orders, equipment
-- Author: Claude
-- Date: 2026-01-16
-- ============================================================================

-- Create pms_attachments table
CREATE TABLE IF NOT EXISTS pms_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Entity association (polymorphic)
    entity_type VARCHAR(50) NOT NULL,
    -- Types: fault, work_order, equipment, checklist_item, note, handover
    entity_id UUID NOT NULL,

    -- File info
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    mime_type VARCHAR(100) NOT NULL,
    file_size INTEGER,  -- bytes
    storage_path TEXT NOT NULL,  -- Supabase storage path

    -- Image-specific fields
    width INTEGER,
    height INTEGER,
    thumbnail_path TEXT,

    -- Metadata
    description TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',

    -- Upload tracking
    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,

    -- Check constraints
    CONSTRAINT chk_pms_attachments_entity_type
        CHECK (entity_type IN ('fault', 'work_order', 'equipment', 'checklist_item', 'note', 'handover', 'purchase_order'))
);

-- Comment on table
COMMENT ON TABLE pms_attachments IS 'File attachments (photos, documents) linked to various entities';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pms_attachments_yacht_id ON pms_attachments(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_attachments_entity ON pms_attachments(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_pms_attachments_uploaded_by ON pms_attachments(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_pms_attachments_mime_type ON pms_attachments(mime_type);

-- Enable Row Level Security
ALTER TABLE pms_attachments ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role bypass
CREATE POLICY service_role_bypass ON pms_attachments
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policy: Users can only access attachments for yachts they have access to
CREATE POLICY yacht_isolation_select ON pms_attachments
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_attachments.yacht_id
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_attachments
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_attachments.yacht_id
        )
    );

CREATE POLICY yacht_isolation_update ON pms_attachments
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_attachments.yacht_id
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_attachments
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR EXISTS (
            SELECT 1 FROM user_accounts
            WHERE user_accounts.auth_user_id = auth.uid()
            AND user_accounts.yacht_id = pms_attachments.yacht_id
        )
    );

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_pms_attachments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_attachments_updated_at ON pms_attachments;
CREATE TRIGGER trg_pms_attachments_updated_at
    BEFORE UPDATE ON pms_attachments
    FOR EACH ROW
    EXECUTE FUNCTION update_pms_attachments_updated_at();
