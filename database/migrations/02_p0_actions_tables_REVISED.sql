-- Migration: 02_p0_actions_tables_REVISED
-- =============================================================================
-- P0 Actions Database Schema - MVP MINIMAL APPROACH
-- =============================================================================
--
-- PURPOSE: Support 8 P0 actions with MINIMAL new schema
-- PHILOSOPHY: Leverage existing tables, add columns where possible, only create new tables where truly justified
--
-- ACTIONS SUPPORTED:
--   1. show_manual_section (documents)
--   2. create_work_order_from_fault (work_orders)
--   3. add_note_to_work_order (work_order_notes)
--   4. add_part_to_work_order (work_order_parts)
--   5. mark_work_order_complete (work_orders + part_usage)
--   6. check_stock_level (parts)
--   7. log_part_usage (part_usage)
--   8. add_to_handover (handover)
--
-- USER FEEDBACK: "those changes on the back end aren't necessarily new tables though?
--                 and they must relate to those adjacent tables in question? inventory etc?
--                 new columns will be needed but argue why new table?"
--
-- DECISION MATRIX:
-- - work_orders: NEW TABLE (justified - core entity for 5 P0 actions, no alternative)
-- - audit_log: NEW TABLE (justified - non-negotiable for accountability)
-- - handover: NEW TABLE (justified - new feature, no existing equivalent)
-- - work_order_notes: NEW TABLE (justified - better than JSONB array for queries)
-- - work_order_parts: NEW TABLE (justified - standard M:M junction table)
-- - part_usage: NEW TABLE (justified - event log pattern for inventory audit)
-- - equipment: CHECK IF EXISTS (handlers reference it, may already exist)
-- - faults: CHECK IF EXISTS (handlers reference it, may already exist)
-- - parts: CHECK IF EXISTS (handlers reference it, if exists add columns)
--
-- =============================================================================

-- =============================================================================
-- SECTION 1: CONDITIONAL BASE TABLES
-- =============================================================================
-- These tables MAY already exist. Only create if missing.
-- TODO: Check actual database before running this migration.

-- -----------------------------------------------------------------------------
-- EQUIPMENT TABLE (May exist)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: Referenced by handlers (equipment_handlers.py, fault_handlers.py)
--                If doesn't exist, create minimal version for MVP.

CREATE TABLE IF NOT EXISTS public.equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    location TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'operational' CHECK (status IN ('operational', 'degraded', 'failed', 'maintenance', 'decommissioned')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(yacht_id, name)
);

CREATE INDEX IF NOT EXISTS idx_equipment_yacht_id ON public.equipment(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_status ON public.equipment(status) WHERE status IN ('operational', 'degraded', 'failed');
CREATE INDEX IF NOT EXISTS idx_equipment_location ON public.equipment(location);

COMMENT ON TABLE public.equipment IS 'Equipment/machinery on yachts - Created by 02_p0_actions_tables_REVISED.sql';

-- -----------------------------------------------------------------------------
-- FAULTS TABLE (May exist)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: Referenced by fault_handlers.py, needed for create_work_order_from_fault action.
--                If doesn't exist, create minimal version for MVP.

CREATE TABLE IF NOT EXISTS public.faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    fault_code TEXT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    reported_by UUID REFERENCES auth.users(id),
    resolved_by UUID REFERENCES auth.users(id),
    resolution_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faults_yacht_id ON public.faults(yacht_id);
CREATE INDEX IF NOT EXISTS idx_faults_equipment_id ON public.faults(equipment_id);
CREATE INDEX IF NOT EXISTS idx_faults_fault_code ON public.faults(fault_code);
CREATE INDEX IF NOT EXISTS idx_faults_active ON public.faults(yacht_id, resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_faults_severity ON public.faults(severity) WHERE resolved_at IS NULL;

COMMENT ON TABLE public.faults IS 'Equipment faults and failures - Created by 02_p0_actions_tables_REVISED.sql';
COMMENT ON COLUMN public.faults.fault_code IS 'OEM fault code (e.g., MTU-OVHT-01)';
COMMENT ON COLUMN public.faults.resolved_at IS 'NULL = active fault, NOT NULL = resolved';

-- -----------------------------------------------------------------------------
-- PARTS TABLE (May exist as 'inventory' or 'pms_parts')
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: Referenced by inventory_handlers.py, needed for parts-related P0 actions.
--                If doesn't exist, create minimal version for MVP.
--                If exists, columns will be added below.

CREATE TABLE IF NOT EXISTS public.parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    part_number TEXT,
    description TEXT,
    manufacturer TEXT,
    category TEXT,
    location TEXT,  -- Physical location on yacht
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER DEFAULT 0,
    unit_price NUMERIC(10,2),
    unit TEXT DEFAULT 'ea',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(yacht_id, part_number)
);

CREATE INDEX IF NOT EXISTS idx_parts_yacht_id ON public.parts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_parts_part_number ON public.parts(part_number);
CREATE INDEX IF NOT EXISTS idx_parts_low_stock ON public.parts(yacht_id, quantity_on_hand, minimum_quantity)
    WHERE quantity_on_hand <= minimum_quantity;
CREATE INDEX IF NOT EXISTS idx_parts_location ON public.parts(location);

COMMENT ON TABLE public.parts IS 'Spare parts inventory - Created by 02_p0_actions_tables_REVISED.sql';
COMMENT ON COLUMN public.parts.quantity_on_hand IS 'Current stock level';
COMMENT ON COLUMN public.parts.minimum_quantity IS 'Reorder threshold';

-- Add columns to parts table if it already exists
-- These columns are needed for P0 Action #6: check_stock_level
DO $$
BEGIN
    -- Add last_counted_at if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'parts'
        AND column_name = 'last_counted_at'
    ) THEN
        ALTER TABLE public.parts ADD COLUMN last_counted_at TIMESTAMPTZ;
        COMMENT ON COLUMN public.parts.last_counted_at IS 'Last physical stock count timestamp';
    END IF;

    -- Add last_counted_by if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'parts'
        AND column_name = 'last_counted_by'
    ) THEN
        ALTER TABLE public.parts ADD COLUMN last_counted_by UUID REFERENCES auth.users(id);
        COMMENT ON COLUMN public.parts.last_counted_by IS 'User who performed last stock count';
    END IF;
END $$;

-- =============================================================================
-- SECTION 2: REQUIRED NEW TABLES (Justified)
-- =============================================================================
-- These tables MUST be created for MVP. No existing alternative.

-- -----------------------------------------------------------------------------
-- WORK ORDERS TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: Core entity for 5 P0 actions:
--                - create_work_order_from_fault
--                - add_note_to_work_order
--                - add_part_to_work_order
--                - mark_work_order_complete
--                - (referenced by check_stock_level, log_part_usage)
--                No existing table provides this functionality.

CREATE TABLE IF NOT EXISTS public.work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    number TEXT NOT NULL,  -- WO-2024-089 (auto-generated)
    title TEXT NOT NULL,
    description TEXT,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    fault_id UUID REFERENCES public.faults(id) ON DELETE SET NULL,
    location TEXT,
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',      -- Created but not started
        'open',          -- Ready to be worked on
        'in_progress',   -- Work has started
        'pending_parts', -- Waiting for parts
        'completed',     -- Work finished
        'closed',        -- Completed and signed off
        'cancelled'      -- Work order cancelled
    )),
    assigned_to UUID REFERENCES auth.users(id),
    due_date TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES auth.users(id),
    completion_notes TEXT,
    closed_at TIMESTAMPTZ,
    closed_by UUID REFERENCES auth.users(id),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, number)
);

CREATE INDEX IF NOT EXISTS idx_work_orders_yacht_id ON public.work_orders(yacht_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_number ON public.work_orders(yacht_id, number);
CREATE INDEX IF NOT EXISTS idx_work_orders_equipment_id ON public.work_orders(equipment_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_fault_id ON public.work_orders(fault_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_status ON public.work_orders(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_work_orders_assigned ON public.work_orders(assigned_to) WHERE status IN ('open', 'in_progress');
CREATE INDEX IF NOT EXISTS idx_work_orders_active ON public.work_orders(yacht_id, created_at DESC) WHERE status NOT IN ('completed', 'closed', 'cancelled');

COMMENT ON TABLE public.work_orders IS 'Work orders for maintenance tasks - REQUIRED for P0 actions';
COMMENT ON COLUMN public.work_orders.number IS 'Auto-generated sequential number per yacht (WO-2024-001)';
COMMENT ON COLUMN public.work_orders.status IS 'Workflow: candidate → open → in_progress → completed → closed';
COMMENT ON COLUMN public.work_orders.fault_id IS 'Optional link to fault that triggered this WO';

-- -----------------------------------------------------------------------------
-- WORK ORDER NOTES TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: P0 Action #3 (add_note_to_work_order) requires storing notes.
--                Separate table is better than JSONB array for:
--                - Query performance (filter/search notes)
--                - Audit trail (who added what when)
--                - Relational integrity

CREATE TABLE IF NOT EXISTS public.work_order_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'general' CHECK (note_type IN ('general', 'progress', 'issue', 'resolution')),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_order_notes_work_order_id ON public.work_order_notes(work_order_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_work_order_notes_created_by ON public.work_order_notes(created_by);

COMMENT ON TABLE public.work_order_notes IS 'Notes/comments on work orders - REQUIRED for add_note_to_work_order action';
COMMENT ON COLUMN public.work_order_notes.note_type IS 'Category: general, progress, issue, resolution';

-- -----------------------------------------------------------------------------
-- WORK ORDER PARTS TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: P0 Action #4 (add_part_to_work_order) requires M:M relationship.
--                Standard junction table pattern for "shopping list" of parts needed.
--                This is NOT inventory deduction - just planning/tracking.

CREATE TABLE IF NOT EXISTS public.work_order_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    notes TEXT,
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(work_order_id, part_id)
);

CREATE INDEX IF NOT EXISTS idx_work_order_parts_work_order_id ON public.work_order_parts(work_order_id);
CREATE INDEX IF NOT EXISTS idx_work_order_parts_part_id ON public.work_order_parts(part_id);

COMMENT ON TABLE public.work_order_parts IS 'Parts needed for work orders (shopping list) - REQUIRED for add_part_to_work_order action';
COMMENT ON COLUMN public.work_order_parts.quantity IS 'Quantity needed (not deducted until WO completion)';

-- -----------------------------------------------------------------------------
-- PART USAGE TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: P0 Actions #5 (mark_work_order_complete) and #7 (log_part_usage) require inventory deduction audit.
--                Event log pattern - each row = one inventory deduction event.
--                Alternative would be audit_log, but separate table is clearer and queryable.
--                Enables:
--                - Usage history per part
--                - Inventory reconciliation
--                - Cost tracking per work order
--                - Audit compliance

CREATE TABLE IF NOT EXISTS public.part_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE SET NULL,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    usage_reason TEXT CHECK (usage_reason IN ('work_order', 'maintenance', 'emergency', 'testing', 'other')),
    notes TEXT,
    used_by UUID NOT NULL REFERENCES auth.users(id),
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_part_usage_yacht_id ON public.part_usage(yacht_id);
CREATE INDEX IF NOT EXISTS idx_part_usage_part_id ON public.part_usage(part_id, used_at DESC);
CREATE INDEX IF NOT EXISTS idx_part_usage_work_order_id ON public.part_usage(work_order_id);
CREATE INDEX IF NOT EXISTS idx_part_usage_equipment_id ON public.part_usage(equipment_id);
CREATE INDEX IF NOT EXISTS idx_part_usage_used_by ON public.part_usage(used_by);

COMMENT ON TABLE public.part_usage IS 'Inventory usage log (deduction events) - REQUIRED for mark_work_order_complete and log_part_usage actions';
COMMENT ON COLUMN public.part_usage.quantity IS 'Quantity consumed (reduces parts.quantity_on_hand)';
COMMENT ON COLUMN public.part_usage.work_order_id IS 'Optional link to work order (if usage was for WO)';

-- -----------------------------------------------------------------------------
-- HANDOVER TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: P0 Action #8 (add_to_handover) is a NEW feature.
--                No existing table provides handover/shift summary functionality.
--                Stores polymorphic references to entities (work orders, faults, equipment).

CREATE TABLE IF NOT EXISTS public.handover (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('work_order', 'fault', 'equipment', 'note')),
    entity_id UUID,  -- Polymorphic reference
    summary_text TEXT NOT NULL,
    category TEXT CHECK (category IN ('urgent', 'in_progress', 'completed', 'watch', 'fyi')),
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 5),
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_handover_yacht_id ON public.handover(yacht_id, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_entity ON public.handover(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_handover_category ON public.handover(yacht_id, category, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_priority ON public.handover(yacht_id, priority DESC, added_at DESC);

COMMENT ON TABLE public.handover IS 'Shift handover items - REQUIRED for add_to_handover action';
COMMENT ON COLUMN public.handover.entity_type IS 'Type of entity being handed over (work_order, fault, equipment, note)';
COMMENT ON COLUMN public.handover.entity_id IS 'Polymorphic FK to entity (use with entity_type)';
COMMENT ON COLUMN public.handover.priority IS '0-5 priority for handover display order';

-- -----------------------------------------------------------------------------
-- AUDIT LOG TABLE - NEW (Justified)
-- -----------------------------------------------------------------------------
-- JUSTIFICATION: NON-NEGOTIABLE for MVP accountability.
--                Every MUTATE action MUST create an audit log entry.
--                User requirement: "auditing, actioning etc. will be required"
--                Enables:
--                - Who did what, when
--                - Signature verification
--                - Compliance (maritime regulations)
--                - Change history
--                - Forensics

CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,  -- e.g., 'create_work_order_from_fault', 'log_part_usage'
    entity_type TEXT NOT NULL,  -- e.g., 'work_order', 'part_usage', 'handover'
    entity_id UUID NOT NULL,  -- ID of created/modified entity
    user_id UUID NOT NULL REFERENCES auth.users(id),
    old_values JSONB,  -- Previous state (for updates)
    new_values JSONB NOT NULL,  -- New state (for creates/updates)
    signature JSONB NOT NULL,  -- {user_id, timestamp, ip_address, ...}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_yacht_id ON public.audit_log(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON public.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON public.audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON public.audit_log(action, created_at DESC);

COMMENT ON TABLE public.audit_log IS 'Audit trail for all mutations - NON-NEGOTIABLE for accountability';
COMMENT ON COLUMN public.audit_log.action IS 'P0 action name (e.g., create_work_order_from_fault)';
COMMENT ON COLUMN public.audit_log.entity_type IS 'Type of entity created/modified';
COMMENT ON COLUMN public.audit_log.entity_id IS 'ID of entity created/modified';
COMMENT ON COLUMN public.audit_log.signature IS 'User signature: {user_id, timestamp, ip_address}';
COMMENT ON COLUMN public.audit_log.old_values IS 'Previous state (NULL for creates)';
COMMENT ON COLUMN public.audit_log.new_values IS 'New state after action';

-- =============================================================================
-- SECTION 3: HELPER FUNCTIONS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Generate Work Order Number
-- -----------------------------------------------------------------------------
-- Auto-generates sequential work order numbers per yacht (WO-2024-001)

CREATE OR REPLACE FUNCTION public.generate_wo_number(p_yacht_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_year TEXT;
    v_count INTEGER;
    v_number TEXT;
BEGIN
    v_year := TO_CHAR(NOW(), 'YYYY');

    -- Get count of work orders this year for this yacht
    SELECT COUNT(*) INTO v_count
    FROM public.work_orders
    WHERE yacht_id = p_yacht_id
      AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    v_count := v_count + 1;

    -- Format: WO-2024-001
    v_number := 'WO-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');

    RETURN v_number;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.generate_wo_number IS 'Generate sequential work order number (WO-YYYY-NNN)';

-- -----------------------------------------------------------------------------
-- Deduct Part Inventory
-- -----------------------------------------------------------------------------
-- Atomically deducts quantity from parts.quantity_on_hand
-- Creates part_usage log entry
-- Returns true if successful, false if insufficient stock

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
    -- Get current quantity (with row lock)
    SELECT quantity_on_hand INTO v_current_quantity
    FROM public.parts
    WHERE id = p_part_id AND yacht_id = p_yacht_id
    FOR UPDATE;

    -- Check if sufficient stock
    IF v_current_quantity IS NULL OR v_current_quantity < p_quantity THEN
        RETURN FALSE;
    END IF;

    v_new_quantity := v_current_quantity - p_quantity;

    -- Update parts table
    UPDATE public.parts
    SET quantity_on_hand = v_new_quantity,
        updated_at = NOW()
    WHERE id = p_part_id AND yacht_id = p_yacht_id;

    -- Create part_usage log entry
    INSERT INTO public.part_usage (
        yacht_id, part_id, work_order_id, equipment_id,
        quantity, usage_reason, notes, used_by, used_at
    ) VALUES (
        p_yacht_id, p_part_id, p_work_order_id, p_equipment_id,
        p_quantity, p_usage_reason, p_notes, p_used_by, NOW()
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.deduct_part_inventory IS 'Atomically deduct inventory and log usage';

-- =============================================================================
-- SECTION 4: ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all new tables
ALTER TABLE public.equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_order_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_order_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.part_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Helper function: Get user's yacht_id
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
    SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- RLS Policies: Yacht Isolation (users can only access data for their yacht)

-- Equipment
CREATE POLICY "Users can view equipment on their yacht"
    ON public.equipment FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Faults
CREATE POLICY "Users can view faults on their yacht"
    ON public.faults FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Parts
CREATE POLICY "Users can view parts on their yacht"
    ON public.parts FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Work Orders
CREATE POLICY "Users can view work orders on their yacht"
    ON public.work_orders FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Users can create work orders on their yacht"
    ON public.work_orders FOR INSERT
    TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Users can update work orders on their yacht"
    ON public.work_orders FOR UPDATE
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Work Order Notes
CREATE POLICY "Users can view notes on their yacht's work orders"
    ON public.work_order_notes FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.work_orders
            WHERE id = work_order_notes.work_order_id
            AND yacht_id = public.get_user_yacht_id()
        )
    );

CREATE POLICY "Users can add notes to their yacht's work orders"
    ON public.work_order_notes FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.work_orders
            WHERE id = work_order_notes.work_order_id
            AND yacht_id = public.get_user_yacht_id()
        )
    );

-- Work Order Parts
CREATE POLICY "Users can view parts on their yacht's work orders"
    ON public.work_order_parts FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.work_orders
            WHERE id = work_order_parts.work_order_id
            AND yacht_id = public.get_user_yacht_id()
        )
    );

CREATE POLICY "Users can add parts to their yacht's work orders"
    ON public.work_order_parts FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.work_orders
            WHERE id = work_order_parts.work_order_id
            AND yacht_id = public.get_user_yacht_id()
        )
    );

-- Part Usage
CREATE POLICY "Users can view part usage on their yacht"
    ON public.part_usage FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Users can log part usage on their yacht"
    ON public.part_usage FOR INSERT
    TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Handover
CREATE POLICY "Users can view handover items on their yacht"
    ON public.handover FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Users can add handover items for their yacht"
    ON public.handover FOR INSERT
    TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Audit Log
CREATE POLICY "Users can view audit log for their yacht"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "Service role can insert audit log entries"
    ON public.audit_log FOR INSERT
    TO service_role
    WITH CHECK (true);

-- =============================================================================
-- SECTION 5: TRIGGERS
-- =============================================================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_equipment_updated_at
    BEFORE UPDATE ON public.equipment
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_faults_updated_at
    BEFORE UPDATE ON public.faults
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_parts_updated_at
    BEFORE UPDATE ON public.parts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_work_orders_updated_at
    BEFORE UPDATE ON public.work_orders
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- =============================================================================
-- END OF MIGRATION
-- =============================================================================

-- Summary of tables created:
-- 1. equipment (if not exists)
-- 2. faults (if not exists)
-- 3. parts (if not exists, + columns added)
-- 4. work_orders (NEW - core entity)
-- 5. work_order_notes (NEW - junction/log)
-- 6. work_order_parts (NEW - junction/shopping list)
-- 7. part_usage (NEW - event log)
-- 8. handover (NEW - feature)
-- 9. audit_log (NEW - accountability)
--
-- Total: 3 conditional base tables + 6 required new tables = 9 tables
-- Previous version: 12 tables (removed: document_sections, attachments, documents)
--
-- Columns added to existing tables:
-- - parts.last_counted_at
-- - parts.last_counted_by
