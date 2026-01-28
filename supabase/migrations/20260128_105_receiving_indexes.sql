-- ============================================================================
-- MIGRATION: 20260128_105_receiving_indexes.sql
-- PURPOSE: Create performance indexes for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- INDEXES:
--   - Primary lookups: yacht_id + received_date, yacht_id + status
--   - Foreign keys: receiving_id, document_id
--   - Search fields: vendor_reference
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE: pms_receiving
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_yacht_date
    ON pms_receiving(yacht_id, received_date DESC);

CREATE INDEX IF NOT EXISTS idx_receiving_yacht_status
    ON pms_receiving(yacht_id, status);

CREATE INDEX IF NOT EXISTS idx_receiving_yacht_vendor_ref
    ON pms_receiving(yacht_id, vendor_reference);

CREATE INDEX IF NOT EXISTS idx_receiving_work_order
    ON pms_receiving(linked_work_order_id)
    WHERE linked_work_order_id IS NOT NULL;

-- ============================================================================
-- TABLE: pms_receiving_items
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_items_yacht_receiving
    ON pms_receiving_items(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_items_yacht_part
    ON pms_receiving_items(yacht_id, part_id)
    WHERE part_id IS NOT NULL;

-- ============================================================================
-- TABLE: pms_receiving_documents
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_documents_yacht_receiving
    ON pms_receiving_documents(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_documents_yacht_doctype
    ON pms_receiving_documents(yacht_id, doc_type)
    WHERE doc_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_receiving_documents_document_id
    ON pms_receiving_documents(document_id);

-- ============================================================================
-- TABLE: pms_receiving_extractions
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_receiving_extractions_yacht_receiving
    ON pms_receiving_extractions(yacht_id, receiving_id);

CREATE INDEX IF NOT EXISTS idx_receiving_extractions_source_doc
    ON pms_receiving_extractions(source_document_id);

COMMIT;

DO $$
DECLARE
    index_count INTEGER;
BEGIN
    -- Count indexes created
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions')
      AND indexname LIKE 'idx_receiving%';

    RAISE NOTICE 'SUCCESS: Created/verified % indexes for Receiving Lens v1', index_count;
END $$;
