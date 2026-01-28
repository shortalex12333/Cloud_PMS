-- Migration: 202601271308_inventory_backfill_locations.sql
-- Purpose: Backfill pms_part_locations from existing TEXT location values
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27
--
-- IMPORTANT: This is a DATA migration, not a schema migration.
-- It should be run AFTER all schema migrations are applied.
-- It is IDEMPOTENT and can be run multiple times safely.

-- ============================================================================
-- STEP 1: Extract unique locations from existing parts
-- ============================================================================

INSERT INTO pms_part_locations (yacht_id, name, created_at)
SELECT DISTINCT yacht_id, location, NOW()
FROM pms_parts
WHERE location IS NOT NULL
  AND location != ''
  AND yacht_id IS NOT NULL
ON CONFLICT (yacht_id, name) DO NOTHING;

-- ============================================================================
-- STEP 2: Populate primary_location_id FK from TEXT location
-- ============================================================================

UPDATE pms_parts p
SET primary_location_id = l.id
FROM pms_part_locations l
WHERE p.location = l.name
  AND p.yacht_id = l.yacht_id
  AND p.primary_location_id IS NULL
  AND p.location IS NOT NULL
  AND p.location != '';

-- ============================================================================
-- STEP 3: Verification queries (run manually to confirm)
-- ============================================================================

-- Check for orphaned locations (parts with TEXT but no FK)
-- SELECT COUNT(*) AS orphaned FROM pms_parts
-- WHERE location IS NOT NULL AND location != '' AND primary_location_id IS NULL;
-- Expected: 0

-- Check location coverage
-- SELECT
--     (SELECT COUNT(DISTINCT location) FROM pms_parts WHERE location IS NOT NULL AND location != '') AS text_locations,
--     (SELECT COUNT(*) FROM pms_part_locations) AS normalized_locations;
-- Expected: text_locations <= normalized_locations

-- ============================================================================
-- STEP 4: DO NOT drop the legacy column yet
-- Only after all apps are updated to use primary_location_id should you run:
-- ALTER TABLE pms_parts DROP COLUMN IF EXISTS location;
-- ============================================================================
