-- Migration: Standard indexes for Show Related FK joins
-- Feature: P1 Show Related - Optimize common query patterns
-- Date: 2026-01-28
-- Idempotent: Safe to rerun; uses IF NOT EXISTS

-- =============================================================================
-- PURPOSE
-- =============================================================================
-- Creates indexes to optimize FK joins and yacht_id filters in Show Related queries
-- These indexes are ALWAYS beneficial (not optional like doc_metadata indexes)
-- Safe to apply; small overhead on writes, large benefit on reads
-- =============================================================================

-- =============================================================================
-- INDEX 1: pms_work_order_parts (parts query - Group 1)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wop_work_order_yacht
ON pms_work_order_parts(work_order_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wop_work_order_yacht IS
'Optimizes: SELECT parts FROM pms_work_order_parts WHERE work_order_id = ? AND yacht_id = ? (Group 1). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX 2: pms_work_orders (equipment-based queries - Groups 2, 3)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wo_equipment_yacht
ON pms_work_orders(equipment_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wo_equipment_yacht IS
'Optimizes: SELECT work_orders WHERE equipment_id = ? AND yacht_id = ? (Groups 2, 3). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX 3: pms_work_orders (last_activity_at sorting - Group 3)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wo_last_activity
ON pms_work_orders(last_activity_at DESC NULLS LAST, created_at DESC)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wo_last_activity IS
'Optimizes: ORDER BY last_activity_at DESC NULLS LAST for previous_work sorting (Group 3). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX 4: pms_entity_links (source lookups - Group 6)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_links_source
ON pms_entity_links(source_entity_type, source_entity_id, yacht_id);

COMMENT ON INDEX idx_entity_links_source IS
'Optimizes: SELECT explicit_links WHERE source_entity_type = ? AND source_entity_id = ? (Group 6). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX 5: pms_entity_links (target lookups - Group 6, bidirectional)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_links_target
ON pms_entity_links(target_entity_type, target_entity_id, yacht_id);

COMMENT ON INDEX idx_entity_links_target IS
'Optimizes: SELECT explicit_links WHERE target_entity_type = ? AND target_entity_id = ? (Group 6, bidirectional). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX 6: pms_work_order_notes (notes query - Group 4)
-- =============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_won_work_order_yacht
ON pms_work_order_notes(work_order_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_won_work_order_yacht IS
'Optimizes: SELECT notes WHERE work_order_id = ? AND yacht_id = ? (Group 4). Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    index_count INT;
BEGIN
    -- Count indexes created by this migration
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename IN ('pms_work_order_parts', 'pms_work_orders', 'pms_entity_links', 'pms_work_order_notes')
      AND indexname IN (
          'idx_wop_work_order_yacht',
          'idx_wo_equipment_yacht',
          'idx_wo_last_activity',
          'idx_entity_links_source',
          'idx_entity_links_target',
          'idx_won_work_order_yacht'
      );

    IF index_count = 6 THEN
        RAISE NOTICE 'Verification passed: All 6 indexes created successfully';
    ELSE
        RAISE WARNING 'Expected 6 indexes, found %', index_count;
    END IF;
END $$;

-- =============================================================================
-- EXPECTED RESULTS
-- =============================================================================
-- All 6 indexes created
-- Queries on Show Related groups now use index scans instead of sequential scans
-- Performance improvement: 10-100x faster for FK joins on large tables

-- =============================================================================
-- ROLLBACK (if indexes cause write performance issues - unlikely)
-- =============================================================================
-- DROP INDEX CONCURRENTLY IF EXISTS idx_wop_work_order_yacht;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_wo_equipment_yacht;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_wo_last_activity;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_entity_links_source;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_entity_links_target;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_won_work_order_yacht;

-- Migration complete
-- All FK join indexes created successfully
