-- Migration: 02_p0_actions_tables
-- P0 Actions Database Schema
-- Implements tables for 8 P0 actions:
--   1. show_manual_section
--   2. create_work_order_from_fault
--   3. add_note_to_work_order
--   4. add_part_to_work_order
--   5. mark_work_order_complete
--   6. check_stock_level
--   7. log_part_usage
--   8. add_to_handover

-- =============================================================================
-- EQUIPMENT TABLE
-- =============================================================================
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
    risk_score NUMERIC(3,2) DEFAULT 0.0 CHECK (risk_score >= 0 AND risk_score <= 1),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, name)
);

CREATE INDEX idx_equipment_yacht_id ON public.equipment(yacht_id);
CREATE INDEX idx_equipment_status ON public.equipment(status) WHERE status IN ('operational', 'degraded', 'failed');
CREATE INDEX idx_equipment_location ON public.equipment(location);

COMMENT ON TABLE public.equipment IS 'Equipment/machinery on yachts';
COMMENT ON COLUMN public.equipment.risk_score IS 'Risk score from predictive analytics (0-1)';

-- =============================================================================
-- FAULTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    fault_code TEXT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reported_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    reported_by UUID REFERENCES auth.users(id),
    resolved_by UUID REFERENCES auth.users(id),
    resolution_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_faults_yacht_id ON public.faults(yacht_id);
CREATE INDEX idx_faults_equipment_id ON public.faults(equipment_id);
CREATE INDEX idx_faults_fault_code ON public.faults(fault_code);
CREATE INDEX idx_faults_active ON public.faults(yacht_id, resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_faults_severity ON public.faults(severity) WHERE resolved_at IS NULL;

COMMENT ON TABLE public.faults IS 'Equipment faults and failures';
COMMENT ON COLUMN public.faults.fault_code IS 'OEM fault code (e.g., MTU-OVHT-01)';
COMMENT ON COLUMN public.faults.resolved_at IS 'NULL = active fault, NOT NULL = resolved';

-- =============================================================================
-- WORK ORDERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    number TEXT NOT NULL,  -- WO-2024-089
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
    closed_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    completed_by UUID REFERENCES auth.users(id),
    completion_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, number)
);

CREATE INDEX idx_work_orders_yacht_id ON public.work_orders(yacht_id);
CREATE INDEX idx_work_orders_equipment_id ON public.work_orders(equipment_id);
CREATE INDEX idx_work_orders_fault_id ON public.work_orders(fault_id);
CREATE INDEX idx_work_orders_status ON public.work_orders(yacht_id, status);
CREATE INDEX idx_work_orders_assigned_to ON public.work_orders(assigned_to) WHERE status IN ('open', 'in_progress');
CREATE INDEX idx_work_orders_priority ON public.work_orders(priority, status) WHERE status IN ('open', 'in_progress');

COMMENT ON TABLE public.work_orders IS 'Maintenance work orders';
COMMENT ON COLUMN public.work_orders.status IS 'candidate = created but not started, open = ready for work, in_progress = work started, completed = work done, closed = signed off';
COMMENT ON COLUMN public.work_orders.fault_id IS 'Optional link to fault that triggered this WO';

-- =============================================================================
-- WORK ORDER NOTES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.work_order_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'general' CHECK (note_type IN ('general', 'progress', 'issue', 'parts', 'completion')),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_work_order_notes_work_order_id ON public.work_order_notes(work_order_id);
CREATE INDEX idx_work_order_notes_created_at ON public.work_order_notes(created_at DESC);

COMMENT ON TABLE public.work_order_notes IS 'Notes/comments on work orders (breadcrumbs for whoever picks up work next)';

-- =============================================================================
-- PARTS TABLE (Inventory)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    part_number TEXT,
    description TEXT,
    category TEXT,
    manufacturer TEXT,
    unit TEXT NOT NULL DEFAULT 'each',  -- 'each', 'kg', 'L', 'm', etc.
    quantity_on_hand NUMERIC(10,2) NOT NULL DEFAULT 0,
    minimum_quantity NUMERIC(10,2) DEFAULT 0,
    maximum_quantity NUMERIC(10,2),
    location TEXT,  -- Physical storage location
    last_counted_at TIMESTAMPTZ,
    last_counted_by UUID REFERENCES auth.users(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, part_number)
);

CREATE INDEX idx_parts_yacht_id ON public.parts(yacht_id);
CREATE INDEX idx_parts_category ON public.parts(category);
CREATE INDEX idx_parts_low_stock ON public.parts(yacht_id, quantity_on_hand, minimum_quantity) WHERE quantity_on_hand <= minimum_quantity;
CREATE INDEX idx_parts_location ON public.parts(location);

COMMENT ON TABLE public.parts IS 'Parts inventory for yachts';
COMMENT ON COLUMN public.parts.quantity_on_hand IS 'Current stock level (updated by part_usage events)';
COMMENT ON COLUMN public.parts.minimum_quantity IS 'Reorder threshold';

-- =============================================================================
-- WORK ORDER PARTS TABLE (Shopping List)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.work_order_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    notes TEXT,
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(work_order_id, part_id)
);

CREATE INDEX idx_work_order_parts_work_order_id ON public.work_order_parts(work_order_id);
CREATE INDEX idx_work_order_parts_part_id ON public.work_order_parts(part_id);

COMMENT ON TABLE public.work_order_parts IS 'Parts assigned to work orders (shopping list, NOT deduction from inventory)';
COMMENT ON COLUMN public.work_order_parts.quantity IS 'Quantity needed (inventory deducted only when WO completed or usage logged)';

-- =============================================================================
-- PART USAGE LOG TABLE (Inventory Deduction Events)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.part_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE SET NULL,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    usage_reason TEXT NOT NULL CHECK (usage_reason IN (
        'work_order',
        'preventive_maintenance',
        'emergency_repair',
        'testing',
        'other'
    )),
    notes TEXT,
    used_by UUID NOT NULL REFERENCES auth.users(id),
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_part_usage_yacht_id ON public.part_usage(yacht_id);
CREATE INDEX idx_part_usage_part_id ON public.part_usage(part_id);
CREATE INDEX idx_part_usage_work_order_id ON public.part_usage(work_order_id);
CREATE INDEX idx_part_usage_used_at ON public.part_usage(used_at DESC);

COMMENT ON TABLE public.part_usage IS 'Part usage event log (inventory deduction events, attributed to user)';
COMMENT ON COLUMN public.part_usage.quantity IS 'Quantity deducted from inventory';

-- =============================================================================
-- DOCUMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    classification TEXT NOT NULL DEFAULT 'operational' CHECK (classification IN ('operational', 'compliance')),
    category TEXT,  -- 'manual', 'certificate', 'sop', 'technical_drawing', etc.
    manufacturer TEXT,
    model TEXT,
    version TEXT,
    storage_path TEXT NOT NULL,  -- Supabase Storage path
    mime_type TEXT,
    size_bytes BIGINT,
    page_count INTEGER,
    source TEXT,  -- 'oem', 'internal', 'regulatory', etc.
    uploaded_by UUID REFERENCES auth.users(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_yacht_id ON public.documents(yacht_id);
CREATE INDEX idx_documents_classification ON public.documents(classification);
CREATE INDEX idx_documents_category ON public.documents(category);
CREATE INDEX idx_documents_manufacturer_model ON public.documents(manufacturer, model);

COMMENT ON TABLE public.documents IS 'Document metadata (files stored in Supabase Storage)';
COMMENT ON COLUMN public.documents.classification IS 'operational = manuals/guides (Add to Handover visible), compliance = certificates (Add to Handover in dropdown)';
COMMENT ON COLUMN public.documents.storage_path IS 'Path in Supabase Storage bucket';

-- =============================================================================
-- DOCUMENT SECTIONS TABLE (Manual Sections)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.document_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    section_title TEXT NOT NULL,
    page_number INTEGER,
    text_content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_document_sections_document_id ON public.document_sections(document_id);
CREATE INDEX idx_document_sections_page_number ON public.document_sections(document_id, page_number);

COMMENT ON TABLE public.document_sections IS 'Sections/chapters within documents (for show_manual_section action)';

-- =============================================================================
-- HANDOVER TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.handover (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('fault', 'work_order', 'equipment', 'document_chunk', 'part')),
    entity_id UUID NOT NULL,  -- No FK constraint (polymorphic reference)
    summary_text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general' CHECK (category IN (
        'ongoing_fault',
        'work_in_progress',
        'important_info',
        'equipment_status',
        'general'
    )),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_handover_yacht_id ON public.handover(yacht_id);
CREATE INDEX idx_handover_entity ON public.handover(entity_type, entity_id);
CREATE INDEX idx_handover_category ON public.handover(category);
CREATE INDEX idx_handover_priority ON public.handover(priority) WHERE priority IN ('high', 'urgent');
CREATE INDEX idx_handover_added_at ON public.handover(added_at DESC);

COMMENT ON TABLE public.handover IS 'Handover notes (note to your future self or person replacing you)';
COMMENT ON COLUMN public.handover.entity_id IS 'Polymorphic reference to fault, work_order, equipment, etc.';

-- =============================================================================
-- ATTACHMENTS TABLE (Photos, Documents)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('work_order', 'fault', 'equipment', 'handover', 'checklist_item')),
    entity_id UUID NOT NULL,  -- No FK constraint (polymorphic)
    filename TEXT NOT NULL,
    mime_type TEXT,
    storage_path TEXT NOT NULL,  -- Supabase Storage path
    size_bytes BIGINT,
    category TEXT,  -- 'photo', 'document', 'video', etc.
    uploaded_by UUID REFERENCES auth.users(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_attachments_yacht_id ON public.attachments(yacht_id);
CREATE INDEX idx_attachments_entity ON public.attachments(entity_type, entity_id);
CREATE INDEX idx_attachments_uploaded_at ON public.attachments(uploaded_at DESC);

COMMENT ON TABLE public.attachments IS 'File attachments (photos, documents, videos) linked to entities';
COMMENT ON COLUMN public.attachments.storage_path IS 'Path in Supabase Storage bucket';

-- =============================================================================
-- AUDIT LOG TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,  -- Action name (e.g., 'create_work_order_from_fault')
    entity_type TEXT NOT NULL,  -- 'work_order', 'fault', 'part', etc.
    entity_id UUID NOT NULL,  -- ID of affected entity
    user_id UUID NOT NULL REFERENCES auth.users(id),
    old_values JSONB,  -- Before state (for updates)
    new_values JSONB,  -- After state
    signature JSONB,  -- {user_id, timestamp} for signed actions
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_yacht_id ON public.audit_log(yacht_id);
CREATE INDEX idx_audit_log_entity ON public.audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_user_id ON public.audit_log(user_id);
CREATE INDEX idx_audit_log_action ON public.audit_log(action);
CREATE INDEX idx_audit_log_created_at ON public.audit_log(created_at DESC);

COMMENT ON TABLE public.audit_log IS 'Audit trail for all MUTATE actions (full history, immutable)';
COMMENT ON COLUMN public.audit_log.signature IS 'Signature data for actions requiring signature';

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Generate work order number
CREATE OR REPLACE FUNCTION public.generate_wo_number(p_yacht_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_year TEXT;
    v_count INTEGER;
    v_number TEXT;
BEGIN
    v_year := TO_CHAR(NOW(), 'YYYY');

    -- Get count of WOs created this year for this yacht
    SELECT COUNT(*) + 1
    INTO v_count
    FROM public.work_orders
    WHERE yacht_id = p_yacht_id
      AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    -- Format: WO-2024-001
    v_number := 'WO-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');

    RETURN v_number;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.generate_wo_number IS 'Generate sequential work order number (WO-YYYY-XXX)';

-- Deduct part from inventory
CREATE OR REPLACE FUNCTION public.deduct_part_inventory(
    p_part_id UUID,
    p_quantity NUMERIC,
    p_user_id UUID,
    p_work_order_id UUID DEFAULT NULL,
    p_equipment_id UUID DEFAULT NULL,
    p_usage_reason TEXT DEFAULT 'work_order',
    p_notes TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_usage_id UUID;
    v_current_stock NUMERIC;
BEGIN
    -- Check current stock
    SELECT quantity_on_hand INTO v_current_stock
    FROM public.parts
    WHERE id = p_part_id
    FOR UPDATE;  -- Lock row for update

    IF v_current_stock IS NULL THEN
        RAISE EXCEPTION 'Part not found: %', p_part_id;
    END IF;

    IF v_current_stock < p_quantity THEN
        RAISE EXCEPTION 'Insufficient stock: % available, % requested', v_current_stock, p_quantity;
    END IF;

    -- Create usage log entry
    INSERT INTO public.part_usage (
        yacht_id,
        part_id,
        work_order_id,
        equipment_id,
        quantity,
        usage_reason,
        notes,
        used_by,
        used_at
    )
    SELECT
        p.yacht_id,
        p_part_id,
        p_work_order_id,
        p_equipment_id,
        p_quantity,
        p_usage_reason,
        p_notes,
        p_user_id,
        NOW()
    FROM public.parts p
    WHERE p.id = p_part_id
    RETURNING id INTO v_usage_id;

    -- Deduct from inventory
    UPDATE public.parts
    SET quantity_on_hand = quantity_on_hand - p_quantity,
        updated_at = NOW()
    WHERE id = p_part_id;

    RETURN v_usage_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.deduct_part_inventory IS 'Deduct part quantity from inventory and create usage log entry';

-- Update part inventory (for stock adjustments)
CREATE OR REPLACE FUNCTION public.update_part_inventory(
    p_part_id UUID,
    p_new_quantity NUMERIC,
    p_user_id UUID
)
RETURNS VOID AS $$
BEGIN
    UPDATE public.parts
    SET quantity_on_hand = p_new_quantity,
        last_counted_at = NOW(),
        last_counted_by = p_user_id,
        updated_at = NOW()
    WHERE id = p_part_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Part not found: %', p_part_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.update_part_inventory IS 'Update part stock level (for cycle counting)';

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_order_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_order_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.part_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Equipment: Users can view/edit equipment on their yacht
CREATE POLICY "Users can view equipment on own yacht"
    ON public.equipment FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can edit equipment on own yacht"
    ON public.equipment FOR ALL
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Faults: Users can view/create/edit faults on their yacht
CREATE POLICY "Users can view faults on own yacht"
    ON public.faults FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can create faults on own yacht"
    ON public.faults FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can edit faults on own yacht"
    ON public.faults FOR UPDATE
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Work Orders: Users can view/create/edit work orders on their yacht
CREATE POLICY "Users can view work orders on own yacht"
    ON public.work_orders FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can create work orders on own yacht"
    ON public.work_orders FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can edit work orders on own yacht"
    ON public.work_orders FOR UPDATE
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Work Order Notes: Users can view/add notes on their yacht's work orders
CREATE POLICY "Users can view WO notes on own yacht"
    ON public.work_order_notes FOR SELECT
    TO authenticated
    USING (
        work_order_id IN (
            SELECT id FROM public.work_orders WHERE yacht_id IN (
                SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can add WO notes on own yacht"
    ON public.work_order_notes FOR INSERT
    TO authenticated
    WITH CHECK (
        work_order_id IN (
            SELECT id FROM public.work_orders WHERE yacht_id IN (
                SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
            )
        )
    );

-- Parts: Users can view/edit parts on their yacht
CREATE POLICY "Users can view parts on own yacht"
    ON public.parts FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "HODs can manage parts on own yacht"
    ON public.parts FOR ALL
    TO authenticated
    USING (
        public.is_hod(auth.uid(), yacht_id)
    );

-- Part Usage: Users can view/log part usage on their yacht
CREATE POLICY "Users can view part usage on own yacht"
    ON public.part_usage FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can log part usage on own yacht"
    ON public.part_usage FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Documents: Users can view documents on their yacht
CREATE POLICY "Users can view documents on own yacht"
    ON public.documents FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Handover: Users can view/add handover entries on their yacht
CREATE POLICY "Users can view handover on own yacht"
    ON public.handover FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can add handover entries on own yacht"
    ON public.handover FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Audit Log: Users can view audit log for their yacht (read-only)
CREATE POLICY "Users can view audit log on own yacht"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
        )
    );

-- Audit Log: Only backend service can insert
CREATE POLICY "Service can insert audit log entries"
    ON public.audit_log FOR INSERT
    TO service_role
    WITH CHECK (true);

-- =============================================================================
-- TRIGGERS (Auto-update updated_at)
-- =============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_equipment_updated_at BEFORE UPDATE ON public.equipment
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_faults_updated_at BEFORE UPDATE ON public.faults
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_work_orders_updated_at BEFORE UPDATE ON public.work_orders
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_parts_updated_at BEFORE UPDATE ON public.parts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON public.documents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================================================
-- SAMPLE DATA (For Development/Testing)
-- =============================================================================

-- Insert sample equipment (if no equipment exists)
-- INSERT INTO public.equipment (yacht_id, name, manufacturer, model, location, category, status)
-- SELECT
--     y.id,
--     'Generator 2',
--     'MTU',
--     '16V4000',
--     'Engine Room Deck 3',
--     'power_generation',
--     'operational'
-- FROM public.yachts y
-- WHERE NOT EXISTS (SELECT 1 FROM public.equipment)
-- LIMIT 1;

-- =============================================================================
-- END OF MIGRATION
-- =============================================================================

COMMENT ON SCHEMA public IS 'CelesteOS P0 Actions Schema - Completed 2026-01-08';
