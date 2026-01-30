-- ============================================================================
-- MIGRATION: 20260129_105_receiving_indexes.sql
-- PURPOSE: Add performance indexes for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-29
-- ============================================================================
-- PERFORMANCE IMPROVEMENTS:
--   - Index on receiving_id foreign keys (items, documents, extractions, audit)
--   - Index on yacht_id for RLS filtering
--   - Composite index on (yacht_id, status) for listing queries
--   - Index on (entity_type, entity_id) for audit lookups
-- ============================================================================

BEGIN;

-- ============================================================================
-- RECEIVING ITEMS INDEXES
-- ============================================================================

-- Index on receiving_id for foreign key lookups (view_history)
CREATE INDEX IF NOT EXISTS idx_receiving_items_receiving_id
ON pms_receiving_items(receiving_id);

-- Composite index for yacht-scoped queries
CREATE INDEX IF NOT EXISTS idx_receiving_items_yacht_receiving
ON pms_receiving_items(yacht_id, receiving_id);

-- ============================================================================
-- RECEIVING DOCUMENTS INDEXES
-- ============================================================================

-- Index on receiving_id for foreign key lookups (view_history)
CREATE INDEX IF NOT EXISTS idx_receiving_documents_receiving_id
ON pms_receiving_documents(receiving_id);

-- Composite index for yacht-scoped queries
CREATE INDEX IF NOT EXISTS idx_receiving_documents_yacht_receiving
ON pms_receiving_documents(yacht_id, receiving_id);

-- ============================================================================
-- RECEIVING EXTRACTIONS INDEXES
-- ============================================================================

-- Index on receiving_id for foreign key lookups
CREATE INDEX IF NOT EXISTS idx_receiving_extractions_receiving_id
ON pms_receiving_extractions(receiving_id);

-- Composite index for yacht-scoped queries
CREATE INDEX IF NOT EXISTS idx_receiving_extractions_yacht_receiving
ON pms_receiving_extractions(yacht_id, receiving_id);

-- ============================================================================
-- RECEIVING HEADER INDEXES
-- ============================================================================

-- Composite index for listing queries (status-filtered, date-ordered)
CREATE INDEX IF NOT EXISTS idx_receiving_yacht_status_date
ON pms_receiving(yacht_id, status, received_date DESC);

-- Index for vendor reference lookups
CREATE INDEX IF NOT EXISTS idx_receiving_vendor_reference
ON pms_receiving(yacht_id, vendor_reference) WHERE vendor_reference IS NOT NULL;

-- Index for linked work orders
CREATE INDEX IF NOT EXISTS idx_receiving_linked_wo
ON pms_receiving(yacht_id, linked_work_order_id) WHERE linked_work_order_id IS NOT NULL;

-- ============================================================================
-- AUDIT LOG INDEXES
-- ============================================================================

-- Composite index for entity audit trail lookups (view_history)
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_created
ON pms_audit_log(entity_type, entity_id, created_at);

-- Index for yacht-scoped audit queries
CREATE INDEX IF NOT EXISTS idx_audit_log_yacht_entity
ON pms_audit_log(yacht_id, entity_type, entity_id);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    -- Count indexes created on receiving tables
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions', 'pms_audit_log')
      AND indexname LIKE 'idx_receiving%' OR indexname LIKE 'idx_audit_log%';

    RAISE NOTICE 'SUCCESS: Created/verified % indexes for Receiving Lens performance', index_count;

    -- Analyze tables to update query planner statistics
    ANALYZE pms_receiving;
    ANALYZE pms_receiving_items;
    ANALYZE pms_receiving_documents;
    ANALYZE pms_receiving_extractions;
    ANALYZE pms_audit_log;

    RAISE NOTICE 'SUCCESS: Analyzed tables for query planner';
END $$;
