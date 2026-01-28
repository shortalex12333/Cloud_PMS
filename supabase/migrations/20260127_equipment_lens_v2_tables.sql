-- ============================================================================
-- Migration: Equipment Lens v2 - Additional Tables
-- ============================================================================
-- Purpose: Create supporting tables for equipment tracking
-- Tables: equipment_hours_log, equipment_status_log, equipment_parts_bom
-- Note: Uses existing table names (equipment, parts, work_orders) not pms_ prefix
-- Lens: Equipment Lens v2
-- Date: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- 1. equipment_hours_log - Running Hours Tracking
-- =============================================================================
-- Tracks running hours for equipment with meters (generators, engines, etc.)
-- Provides audit trail for hour readings and computed usage

CREATE TABLE IF NOT EXISTS public.equipment_hours_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.equipment(id) ON DELETE CASCADE,

    -- Hour reading
    hours_reading NUMERIC(12, 2) NOT NULL,
    reading_type TEXT NOT NULL DEFAULT 'manual' CHECK (reading_type IN (
        'manual',      -- Crew entered reading
        'automatic',   -- From telemetry/sensor
        'estimated',   -- Computed from usage patterns
        'rollover'     -- Meter rollover correction
    )),

    -- Computed values (from trigger)
    hours_since_last NUMERIC(12, 2),
    daily_average NUMERIC(12, 2),

    -- Context
    notes TEXT,
    source TEXT,  -- 'celeste', 'email_import', 'telemetry', etc.

    -- Audit fields
    recorded_by UUID NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_hours_positive CHECK (hours_reading >= 0)
);

-- Indexes for equipment_hours_log
CREATE INDEX IF NOT EXISTS idx_equipment_hours_yacht_eq
    ON public.equipment_hours_log(yacht_id, equipment_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_equipment_hours_latest
    ON public.equipment_hours_log(equipment_id, recorded_at DESC);

COMMENT ON TABLE public.equipment_hours_log IS 'Running hours log for equipment with meters - Equipment Lens v2';


-- =============================================================================
-- 2. equipment_status_log - Status History Tracking
-- =============================================================================
-- Immutable log of status transitions for equipment
-- Used for lifecycle analysis, downtime tracking, and audit

CREATE TABLE IF NOT EXISTS public.equipment_status_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.equipment(id) ON DELETE CASCADE,

    -- Status transition
    old_status TEXT,
    new_status TEXT NOT NULL CHECK (new_status IN (
        'operational', 'degraded', 'failed', 'maintenance', 'decommissioned'
    )),

    -- Context
    reason TEXT,
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE SET NULL,
    fault_id UUID REFERENCES public.faults(id) ON DELETE SET NULL,

    -- Duration (computed by trigger on next status change)
    duration_hours NUMERIC(12, 2),

    -- Audit fields
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for equipment_status_log
CREATE INDEX IF NOT EXISTS idx_equipment_status_yacht_eq
    ON public.equipment_status_log(yacht_id, equipment_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_equipment_status_new
    ON public.equipment_status_log(yacht_id, new_status);
CREATE INDEX IF NOT EXISTS idx_equipment_status_wo
    ON public.equipment_status_log(work_order_id)
    WHERE work_order_id IS NOT NULL;

COMMENT ON TABLE public.equipment_status_log IS 'Status transition history for equipment - Equipment Lens v2';


-- =============================================================================
-- 3. equipment_parts_bom - Bill of Materials
-- =============================================================================
-- Links equipment to required parts for maintenance

CREATE TABLE IF NOT EXISTS public.equipment_parts_bom (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.equipment(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,

    -- Requirements
    quantity_required INTEGER NOT NULL DEFAULT 1,
    is_critical BOOLEAN NOT NULL DEFAULT false,  -- Critical for operation

    -- Context
    notes TEXT,
    service_interval_hours INTEGER,  -- Replace every N hours

    -- Audit fields
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate links
    CONSTRAINT uq_equipment_part UNIQUE (equipment_id, part_id)
);

-- Indexes for equipment_parts_bom
CREATE INDEX IF NOT EXISTS idx_equipment_parts_yacht_eq
    ON public.equipment_parts_bom(yacht_id, equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_parts_part
    ON public.equipment_parts_bom(part_id);
CREATE INDEX IF NOT EXISTS idx_equipment_parts_critical
    ON public.equipment_parts_bom(equipment_id)
    WHERE is_critical = true;

COMMENT ON TABLE public.equipment_parts_bom IS 'Equipment-to-Parts Bill of Materials - Equipment Lens v2';


-- =============================================================================
-- 4. Add missing columns to equipment table
-- =============================================================================

-- Add attention_flag if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'attention_flag'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN attention_flag BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Add attention_reason if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'attention_reason'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN attention_reason TEXT;
    END IF;
END $$;

-- Add attention_updated_at if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'attention_updated_at'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN attention_updated_at TIMESTAMPTZ;
    END IF;
END $$;

-- Add parent_id if not exists (for equipment hierarchy)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'parent_id'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN parent_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_equipment_parent ON public.equipment(parent_id);
    END IF;
END $$;

-- Add running_hours if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'running_hours'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN running_hours NUMERIC(12, 2) DEFAULT 0;
    END IF;
END $$;

-- Add updated_by if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN updated_by UUID;
    END IF;
END $$;

-- Add soft delete columns if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN deleted_at TIMESTAMPTZ;
        ALTER TABLE public.equipment ADD COLUMN deleted_by UUID;
        ALTER TABLE public.equipment ADD COLUMN deletion_reason TEXT;
        CREATE INDEX IF NOT EXISTS idx_equipment_active ON public.equipment(yacht_id) WHERE deleted_at IS NULL;
    END IF;
END $$;

-- Add is_critical if not exists (separate from attention)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'equipment' AND column_name = 'is_critical'
    ) THEN
        ALTER TABLE public.equipment ADD COLUMN is_critical BOOLEAN DEFAULT false;
    END IF;
END $$;


-- =============================================================================
-- 5. Create notes table if not exists
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Entity association (polymorphic)
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE CASCADE,
    fault_id UUID REFERENCES public.faults(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE CASCADE,

    -- Note content
    text TEXT NOT NULL,
    note_type TEXT DEFAULT 'observation' CHECK (note_type IN (
        'observation', 'inspection', 'handover', 'defect', 'maintenance', 'general'
    )),
    requires_ack BOOLEAN DEFAULT false,
    acked_by UUID,
    acked_at TIMESTAMPTZ,

    -- Attachments
    attachments JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Audit fields
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

-- Indexes for notes
CREATE INDEX IF NOT EXISTS idx_notes_yacht ON public.notes(yacht_id);
CREATE INDEX IF NOT EXISTS idx_notes_equipment ON public.notes(equipment_id) WHERE equipment_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_fault ON public.notes(fault_id) WHERE fault_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_work_order ON public.notes(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_created ON public.notes(yacht_id, created_at DESC);

COMMENT ON TABLE public.notes IS 'Notes for equipment, faults, work orders - Equipment Lens v2';


-- =============================================================================
-- 6. Create attachments table if not exists
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Entity association (polymorphic)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'equipment', 'fault', 'work_order', 'note', 'checklist_item', 'handover', 'purchase_order'
    )),
    entity_id UUID NOT NULL,

    -- File info
    filename TEXT NOT NULL,
    original_filename TEXT,
    mime_type TEXT NOT NULL,
    file_size INTEGER,
    storage_path TEXT NOT NULL,

    -- Image-specific
    width INTEGER,
    height INTEGER,
    thumbnail_path TEXT,

    -- Metadata
    description TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Upload tracking
    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

-- Indexes for attachments
CREATE INDEX IF NOT EXISTS idx_attachments_yacht ON public.attachments(yacht_id);
CREATE INDEX IF NOT EXISTS idx_attachments_entity ON public.attachments(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attachments_uploaded ON public.attachments(uploaded_by);

COMMENT ON TABLE public.attachments IS 'File attachments for various entities - Equipment Lens v2';


-- =============================================================================
-- 7. Create audit_log table if not exists (for equipment actions)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Action details
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,

    -- Actor
    user_id UUID NOT NULL,

    -- Changes
    old_values JSONB,
    new_values JSONB NOT NULL,

    -- Signature (NEVER NULL - {} for non-signed, full payload for signed)
    signature JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for audit_log
CREATE INDEX IF NOT EXISTS idx_audit_log_yacht ON public.audit_log(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON public.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON public.audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON public.audit_log(action, created_at DESC);

COMMENT ON TABLE public.audit_log IS 'Audit trail for all mutations - signature invariant: NEVER NULL';


-- =============================================================================
-- 8. Verification
-- =============================================================================
DO $$
DECLARE
    table_count INTEGER;
    col_count INTEGER;
BEGIN
    -- Check new tables created
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('equipment_hours_log', 'equipment_status_log', 'equipment_parts_bom', 'notes', 'attachments', 'audit_log');

    -- Check equipment columns added
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'equipment'
    AND column_name IN ('attention_flag', 'attention_reason', 'running_hours', 'parent_id', 'deleted_at');

    RAISE NOTICE 'SUCCESS: Equipment Lens v2 tables migration complete';
    RAISE NOTICE '  - New tables: %', table_count;
    RAISE NOTICE '  - Equipment columns added: %', col_count;
END $$;

COMMIT;
