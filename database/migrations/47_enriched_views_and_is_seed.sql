-- Migration 47: Enriched views + is_seed test data isolation
--
-- Adds is_seed boolean column to pms_work_orders, pms_faults, pms_parts.
-- Creates enriched views that JOIN equipment names and assigned_to names,
-- with is_seed=false filter built in.
--
-- Context: V2 review (2.8/10) identified 6,185 test work orders flooding
-- production display. is_seed isolates test data at the query level.
-- Views provide equipment_name and assigned_to_name for frontend list views
-- without requiring additional lookups.
--
-- Date: 2026-03-29

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 1: Add is_seed columns (idempotent)
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE pms_work_orders ADD COLUMN IF NOT EXISTS is_seed BOOLEAN DEFAULT true;
ALTER TABLE pms_faults ADD COLUMN IF NOT EXISTS is_seed BOOLEAN DEFAULT true;
ALTER TABLE pms_parts ADD COLUMN IF NOT EXISTS is_seed BOOLEAN DEFAULT true;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 2: Create enriched views
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_work_orders_enriched AS
SELECT
  wo.*,
  e.name AS equipment_name,
  p.name AS assigned_to_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON e.id = wo.equipment_id
LEFT JOIN auth_users_profiles p ON p.id = wo.assigned_to
WHERE wo.is_seed = false;

CREATE OR REPLACE VIEW v_faults_enriched AS
SELECT
  f.*,
  e.name AS equipment_name
FROM pms_faults f
LEFT JOIN pms_equipment e ON e.id = f.equipment_id
WHERE f.is_seed = false;

CREATE OR REPLACE VIEW v_parts_enriched AS
SELECT
  p.*
FROM pms_parts p
WHERE p.is_seed = false;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 3: Grant access to views
-- ═══════════════════════════════════════════════════════════════════════════

GRANT SELECT ON v_work_orders_enriched TO authenticated;
GRANT SELECT ON v_work_orders_enriched TO anon;
GRANT SELECT ON v_faults_enriched TO authenticated;
GRANT SELECT ON v_faults_enriched TO anon;
GRANT SELECT ON v_parts_enriched TO authenticated;
GRANT SELECT ON v_parts_enriched TO anon;
