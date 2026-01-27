-- Migration: 202601271302_inventory_add_soft_delete_cols.sql
-- Purpose: Add soft delete columns and primary_location_id FK to pms_parts
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- ADD COLUMNS TO pms_parts
-- ============================================================================

-- Soft delete columns
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID,
ADD COLUMN IF NOT EXISTS deletion_reason TEXT;

-- Desired quantity (target stock level)
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS desired_quantity INTEGER;

-- FK to normalized locations
-- Note: The column may already exist without FK constraint
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS primary_location_id UUID;

-- Add FK constraint if not exists (RESTRICT prevents orphaning)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'pms_parts'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'pms_parts_primary_location_id_fkey'
    ) THEN
        ALTER TABLE pms_parts
        ADD CONSTRAINT pms_parts_primary_location_id_fkey
        FOREIGN KEY (primary_location_id)
        REFERENCES pms_part_locations(id)
        ON DELETE RESTRICT;
    END IF;
END
$$;

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for active parts (exclude soft-deleted)
CREATE INDEX IF NOT EXISTS idx_pms_parts_active
ON pms_parts (yacht_id)
WHERE deleted_at IS NULL;

-- Index for location FK
CREATE INDEX IF NOT EXISTS idx_pms_parts_primary_location
ON pms_parts (primary_location_id)
WHERE primary_location_id IS NOT NULL;

-- ============================================================================
-- BACKFILL: Populate primary_location_id from TEXT location
-- Run this AFTER 202601271301_inventory_create_part_locations.sql
-- ============================================================================
-- UPDATE pms_parts p
-- SET primary_location_id = l.id
-- FROM pms_part_locations l
-- WHERE p.location = l.name
--   AND p.yacht_id = l.yacht_id
--   AND p.primary_location_id IS NULL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'pms_parts'
-- AND column_name IN ('deleted_at', 'deleted_by', 'deletion_reason', 'desired_quantity', 'primary_location_id');
-- Should return 5 rows
