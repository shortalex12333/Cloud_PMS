-- ============================================================================
-- EQUIPMENT TABLE - Core PMS Entity
-- ============================================================================
-- Master list of all systems, subsystems, components on the yacht.
-- This is the central entity that work_orders, faults, notes link to.

CREATE TABLE IF NOT EXISTS public.equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,

    -- Identification
    name TEXT NOT NULL,
    code TEXT,                          -- Tag/label e.g. ME1, GEN2, HVAC-AFT
    description TEXT,

    -- Location & Classification
    location TEXT,                      -- Engine room, aft, bridge, etc.
    system_type TEXT,                   -- 'main_engine', 'generator', 'hvac', 'navigation', etc.
    criticality TEXT DEFAULT 'medium' CHECK (criticality IN ('low', 'medium', 'high', 'critical')),

    -- Manufacturer Info
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    installed_date DATE,

    -- Status
    status TEXT DEFAULT 'operational' CHECK (status IN ('operational', 'degraded', 'offline', 'decommissioned')),

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.equipment IS 'Master equipment registry - all systems, subsystems, components';
COMMENT ON COLUMN public.equipment.parent_id IS 'Self-referential FK for equipment hierarchy (e.g., pump belongs to engine)';
COMMENT ON COLUMN public.equipment.code IS 'Short identifier like ME1, GEN2 used in tags and voice commands';
COMMENT ON COLUMN public.equipment.criticality IS 'Impact level if equipment fails';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_equipment_yacht_id ON public.equipment(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_parent_id ON public.equipment(parent_id);
CREATE INDEX IF NOT EXISTS idx_equipment_code ON public.equipment(yacht_id, code);
CREATE INDEX IF NOT EXISTS idx_equipment_system_type ON public.equipment(yacht_id, system_type);
CREATE INDEX IF NOT EXISTS idx_equipment_status ON public.equipment(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_equipment_name_gin ON public.equipment USING gin (name gin_trgm_ops);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 021 Complete - Created equipment table';
END $$;
