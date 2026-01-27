-- ============================================================================
-- MIGRATION: Add Performance Indexes for Fault Lens
-- ============================================================================
-- PROBLEM: Fault queries may be slow without proper indexes
-- SOLUTION: Add composite indexes for common query patterns
-- SEVERITY: P2 - Performance Improvement
-- LENS: Fault Lens v1
-- DATE: 2026-01-27
-- ============================================================================

-- pms_faults indexes (skip if table doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_faults') THEN
        RAISE NOTICE 'pms_faults table does not exist - skipping fault indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_faults_active ON pms_faults (yacht_id, status, detected_at DESC) WHERE status IN (''open'', ''investigating'', ''work_ordered'')';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_faults_equipment_history ON pms_faults (yacht_id, equipment_id, detected_at DESC)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_faults_severity ON pms_faults (yacht_id, severity, status) WHERE severity IN (''critical'', ''safety'')';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_faults_resolved ON pms_faults (yacht_id, resolved_at DESC) WHERE resolved_at IS NOT NULL';
        RAISE NOTICE 'SUCCESS: pms_faults performance indexes created';
    END IF;
END $$;

-- pms_notes indexes (skip if table doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_notes') THEN
        RAISE NOTICE 'pms_notes table does not exist - skipping notes indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_notes_fault ON pms_notes (yacht_id, fault_id, created_at DESC) WHERE fault_id IS NOT NULL';
        RAISE NOTICE 'SUCCESS: pms_notes fault index created';
    END IF;
END $$;

-- pms_attachments indexes (skip if table doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_attachments') THEN
        RAISE NOTICE 'pms_attachments table does not exist - skipping attachments indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pms_attachments_fault ON pms_attachments (yacht_id, entity_id, uploaded_at DESC) WHERE entity_type = ''fault'' AND deleted_at IS NULL';
        RAISE NOTICE 'SUCCESS: pms_attachments fault index created';
    END IF;
END $$;
