-- ============================================================================
-- MIGRATION: 20260127_006_equipment_indexes.sql
-- PURPOSE: Create Equipment Lens v2 indexes per Phase 2 spec
-- LENS: Equipment Lens v2
-- ============================================================================

-- pms_equipment indexes (from Phase 2 DB TRUTH)
CREATE INDEX IF NOT EXISTS idx_equipment_yacht_id ON pms_equipment(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_code ON pms_equipment(code) WHERE code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_parent_id ON pms_equipment(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_system_type ON pms_equipment(system_type) WHERE system_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_criticality ON pms_equipment(criticality) WHERE criticality IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_location ON pms_equipment(yacht_id, location) WHERE location IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_manufacturer ON pms_equipment(yacht_id, manufacturer) WHERE manufacturer IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_equipment_attention_flag ON pms_equipment(attention_flag) WHERE attention_flag = true;
CREATE INDEX IF NOT EXISTS idx_pms_equipment_status ON pms_equipment(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_deleted ON pms_equipment(deleted_at) WHERE deleted_at IS NOT NULL;

-- pms_equipment_hours_log indexes
CREATE INDEX IF NOT EXISTS idx_equipment_hours_log_equipment ON pms_equipment_hours_log(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_hours_log_yacht_date ON pms_equipment_hours_log(yacht_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_equipment_hours_log_source ON pms_equipment_hours_log(source);

-- pms_equipment_status_log indexes
CREATE INDEX IF NOT EXISTS idx_equipment_status_log_equipment ON pms_equipment_status_log(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_status_log_yacht_date ON pms_equipment_status_log(yacht_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_equipment_status_log_new_status ON pms_equipment_status_log(new_status);
CREATE INDEX IF NOT EXISTS idx_equipment_status_log_work_order ON pms_equipment_status_log(work_order_id) WHERE work_order_id IS NOT NULL;

-- pms_equipment_documents indexes
CREATE INDEX IF NOT EXISTS idx_equipment_documents_equipment ON pms_equipment_documents(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_documents_yacht ON pms_equipment_documents(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_documents_type ON pms_equipment_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_equipment_documents_uploaded ON pms_equipment_documents(uploaded_at DESC);

-- pms_equipment_parts_bom indexes (verify/add)
CREATE INDEX IF NOT EXISTS idx_equipment_bom_equipment ON pms_equipment_parts_bom(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_bom_part ON pms_equipment_parts_bom(part_id);
CREATE INDEX IF NOT EXISTS idx_equipment_bom_yacht ON pms_equipment_parts_bom(yacht_id);

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment Lens v2 indexes created';
END $$;
