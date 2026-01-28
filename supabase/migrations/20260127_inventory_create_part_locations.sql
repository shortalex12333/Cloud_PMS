-- Migration: 202601271301_inventory_create_part_locations.sql
-- Purpose: Create normalized pms_part_locations table
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- TABLE: pms_part_locations
-- Normalized storage locations for FK integrity and per-location tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_part_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT,  -- Hierarchical path: "Deck > Forward > Store A"
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,

    -- Unique location names per yacht
    CONSTRAINT uq_part_locations_yacht_name UNIQUE (yacht_id, name)
);

-- Enable RLS
ALTER TABLE pms_part_locations ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- SELECT: All authenticated users can view locations
CREATE POLICY "crew_select_locations" ON pms_part_locations
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE/DELETE: HOD only
CREATE POLICY "hod_manage_locations" ON pms_part_locations
    FOR ALL TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_locations" ON pms_part_locations
    FOR ALL TO service_role
    USING (true);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_part_locations_yacht
ON pms_part_locations (yacht_id);

-- ============================================================================
-- BACKFILL: Migrate existing TEXT locations to normalized table
-- Run this AFTER the migration to populate from existing pms_parts.location
-- ============================================================================
-- INSERT INTO pms_part_locations (yacht_id, name, created_at)
-- SELECT DISTINCT yacht_id, location, NOW()
-- FROM pms_parts
-- WHERE location IS NOT NULL AND location != ''
-- ON CONFLICT (yacht_id, name) DO NOTHING;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'pms_part_locations';
-- Should show: relrowsecurity = true
