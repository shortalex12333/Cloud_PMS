-- ============================================================================
-- MIGRATION: 20260127_019_update_status_constraint.sql
-- PURPOSE: Update pms_equipment status constraint to include all Equipment Lens v2 values
-- LENS: Equipment Lens v2
-- NOTE: Adds 'archived', 'in_service', 'out_of_service' to existing constraint
-- ============================================================================

-- Drop existing status constraint
ALTER TABLE public.pms_equipment
DROP CONSTRAINT IF EXISTS pms_equipment_status_check;

-- Add updated constraint with all Equipment Lens v2 status values
ALTER TABLE public.pms_equipment
ADD CONSTRAINT pms_equipment_status_check CHECK (
    status IN (
        'operational',      -- Normal operation
        'degraded',         -- Reduced performance
        'failed',           -- Not functioning
        'maintenance',      -- Under maintenance
        'out_of_service',   -- NEW: Requires linked OPEN/IN_PROGRESS WO
        'in_service',       -- NEW: Default restored state (from archived)
        'archived',         -- NEW: Reversible archive (can restore to in_service)
        'decommissioned'    -- Terminal state (cannot be restored)
    )
);

COMMENT ON CONSTRAINT pms_equipment_status_check ON public.pms_equipment IS
    'Equipment Lens v2 status values: operational, degraded, failed, maintenance, out_of_service (requires WO), in_service (restored), archived (reversible), decommissioned (terminal)';

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: pms_equipment status constraint updated with Equipment Lens v2 values';
END $$;
