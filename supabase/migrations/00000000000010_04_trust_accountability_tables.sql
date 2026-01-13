-- Migration: 04_trust_accountability_tables
-- =============================================================================
-- Trust & Accountability Tables - NO "Black Box" Systems
-- =============================================================================
--
-- NOTE: This migration creates tables with IF NOT EXISTS since some may
-- already exist from 02_p0_actions_tables_REVISED.sql with different names
--
-- Table mapping (this migration → p0 actions):
--   pms_audit_log → audit_log
--   pms_part_usage → part_usage
--   pms_work_order_notes → work_order_notes
--   pms_handover → handover
--
-- =============================================================================

-- =============================================================================
-- 1. audit_log - Complete Audit Trail (may already exist)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    signature JSONB NOT NULL DEFAULT '{}'::jsonb,
    old_values JSONB,
    new_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Add missing columns if table existed without them
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_log' AND column_name = 'signature') THEN
        ALTER TABLE public.audit_log ADD COLUMN signature JSONB NOT NULL DEFAULT '{}'::jsonb;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_log' AND column_name = 'old_values') THEN
        ALTER TABLE public.audit_log ADD COLUMN old_values JSONB;
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'audit_log column additions skipped: %', SQLERRM;
END $$;

-- Indexes (if not exist)
CREATE INDEX IF NOT EXISTS idx_audit_log_yacht ON audit_log(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action, created_at DESC);

-- RLS
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view audit log for their yacht" ON public.audit_log;
CREATE POLICY "Users can view audit log for their yacht"
ON public.audit_log FOR SELECT
TO authenticated
USING (
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
    OR
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
);

DROP POLICY IF EXISTS "Service role can insert audit entries" ON public.audit_log;
CREATE POLICY "Service role can insert audit entries"
ON public.audit_log FOR INSERT
TO service_role
WITH CHECK (true);

-- =============================================================================
-- 2. part_usage - Inventory Deduction Transparency (may already exist)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.part_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE SET NULL,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    usage_reason TEXT NOT NULL DEFAULT 'work_order' CHECK (usage_reason IN (
        'work_order', 'maintenance', 'emergency', 'testing', 'other'
    )),
    notes TEXT,
    used_by UUID NOT NULL REFERENCES auth.users(id),
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_part_usage_yacht ON part_usage(yacht_id, used_at DESC);
CREATE INDEX IF NOT EXISTS idx_part_usage_part ON part_usage(part_id, used_at DESC);
CREATE INDEX IF NOT EXISTS idx_part_usage_wo ON part_usage(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_part_usage_user ON part_usage(used_by, used_at DESC);

-- RLS
ALTER TABLE public.part_usage ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view part usage on their yacht" ON public.part_usage;
CREATE POLICY "Users can view part usage on their yacht"
ON public.part_usage FOR SELECT
TO authenticated
USING (
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
    OR
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
);

DROP POLICY IF EXISTS "Users can log part usage on their yacht" ON public.part_usage;
CREATE POLICY "Users can log part usage on their yacht"
ON public.part_usage FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
    OR
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
);

-- =============================================================================
-- 3. work_order_notes - Communication Transparency (may already exist)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.work_order_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'general' CHECK (note_type IN (
        'general', 'progress', 'issue', 'resolution'
    )),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_wo_notes_wo ON work_order_notes(work_order_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wo_notes_user ON work_order_notes(created_by, created_at DESC);

-- RLS
ALTER TABLE public.work_order_notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view notes on their yacht work orders" ON public.work_order_notes;
CREATE POLICY "Users can view notes on their yacht work orders"
ON public.work_order_notes FOR SELECT
TO authenticated
USING (
    work_order_id IN (
        SELECT id FROM public.work_orders
        WHERE yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
            UNION
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    )
);

DROP POLICY IF EXISTS "Users can add notes to their yacht work orders" ON public.work_order_notes;
CREATE POLICY "Users can add notes to their yacht work orders"
ON public.work_order_notes FOR INSERT
TO authenticated
WITH CHECK (
    work_order_id IN (
        SELECT id FROM public.work_orders
        WHERE yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
            UNION
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    )
);

-- =============================================================================
-- 4. handover - Shift Accountability (may already exist)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.handover (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'work_order', 'fault', 'equipment', 'note'
    )),
    entity_id UUID,
    summary_text TEXT NOT NULL,
    category TEXT CHECK (category IN (
        'urgent', 'in_progress', 'completed', 'watch', 'fyi'
    )),
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 5),
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_yacht ON handover(yacht_id, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_entity ON handover(entity_type, entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_handover_category ON handover(yacht_id, category, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_priority ON handover(yacht_id, priority DESC, added_at DESC);

-- RLS
ALTER TABLE public.handover ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view handover items on their yacht" ON public.handover;
CREATE POLICY "Users can view handover items on their yacht"
ON public.handover FOR SELECT
TO authenticated
USING (
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
    OR
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
);

DROP POLICY IF EXISTS "Users can add handover items for their yacht" ON public.handover;
CREATE POLICY "Users can add handover items for their yacht"
ON public.handover FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
    OR
    yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    )
);

-- =============================================================================
-- 5. Helper Function: deduct_part_inventory
-- =============================================================================

CREATE OR REPLACE FUNCTION public.deduct_part_inventory(
    p_yacht_id UUID,
    p_part_id UUID,
    p_quantity INTEGER,
    p_work_order_id UUID,
    p_equipment_id UUID,
    p_usage_reason TEXT,
    p_notes TEXT,
    p_used_by UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_current_quantity INTEGER;
    v_new_quantity INTEGER;
BEGIN
    SELECT quantity_on_hand INTO v_current_quantity
    FROM public.parts
    WHERE id = p_part_id AND yacht_id = p_yacht_id
    FOR UPDATE;

    IF v_current_quantity IS NULL OR v_current_quantity < p_quantity THEN
        RETURN FALSE;
    END IF;

    v_new_quantity := v_current_quantity - p_quantity;

    UPDATE public.parts
    SET quantity_on_hand = v_new_quantity,
        updated_at = NOW()
    WHERE id = p_part_id AND yacht_id = p_yacht_id;

    INSERT INTO public.part_usage (
        yacht_id, part_id, work_order_id, equipment_id,
        quantity, usage_reason, notes, used_by, used_at
    ) VALUES (
        p_yacht_id, p_part_id, p_work_order_id, p_equipment_id,
        p_quantity, p_usage_reason, p_notes, p_used_by, NOW()
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- Validation
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log') THEN
        RAISE EXCEPTION 'Failed to create/find audit_log';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'part_usage') THEN
        RAISE EXCEPTION 'Failed to create/find part_usage';
    END IF;

    RAISE NOTICE 'Migration 04_trust_accountability_tables completed successfully';
END $$;
