-- Migration: Create document_object_links table
-- Purpose: Generic linking of documents to any object type (work_order, equipment, handover, etc.)
-- SOC-2: Yacht isolation, audit trail, soft delete

-- Create the document_object_links table
CREATE TABLE IF NOT EXISTS document_object_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Document reference (FK to doc_yacht_library)
    document_id UUID NOT NULL,

    -- Target object (polymorphic)
    object_type TEXT NOT NULL CHECK (object_type IN ('work_order', 'equipment', 'handover', 'fault', 'part', 'receiving', 'purchase_order')),
    object_id UUID NOT NULL,

    -- Link metadata
    link_reason TEXT,  -- 'email_attachment', 'manual', 'auto_linked'
    source_context JSONB,  -- e.g., { email_message_id, email_thread_id }

    -- Lifecycle tracking
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID,
    removed_at TIMESTAMPTZ,
    removed_by UUID,

    -- Indexes
    CONSTRAINT fk_document_object_links_yacht
        FOREIGN KEY (yacht_id) REFERENCES yachts(id) ON DELETE CASCADE,
    CONSTRAINT fk_document_object_links_document
        FOREIGN KEY (document_id) REFERENCES doc_yacht_library(id) ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_document_object_links_yacht_id
    ON document_object_links(yacht_id);
CREATE INDEX IF NOT EXISTS idx_document_object_links_document_id
    ON document_object_links(document_id);
CREATE INDEX IF NOT EXISTS idx_document_object_links_object
    ON document_object_links(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_document_object_links_active
    ON document_object_links(yacht_id, is_active) WHERE is_active = true;

-- Unique constraint: prevent duplicate active links
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_object_links_unique_active
    ON document_object_links(yacht_id, document_id, object_type, object_id)
    WHERE is_active = true;

-- RLS policies
ALTER TABLE document_object_links ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see links for their yacht
CREATE POLICY "document_object_links_yacht_isolation" ON document_object_links
    FOR ALL
    USING (yacht_id = current_setting('app.current_yacht_id', true)::uuid);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON document_object_links TO authenticated;

COMMENT ON TABLE document_object_links IS 'Links documents to objects (work orders, equipment, etc.) - SOC-2 compliant with audit trail';
COMMENT ON COLUMN document_object_links.object_type IS 'Target object type: work_order, equipment, handover, fault, part, receiving, purchase_order';
COMMENT ON COLUMN document_object_links.link_reason IS 'How the link was created: email_attachment, manual, auto_linked';
COMMENT ON COLUMN document_object_links.source_context IS 'Context about link source, e.g., email message/thread IDs';
