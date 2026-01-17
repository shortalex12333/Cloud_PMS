-- =============================================================================
-- Migration: Create Core PMS Tables
-- =============================================================================
-- Purpose: Create pms_equipment and pms_work_orders tables that are required
--          by subsequent migrations
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. pms_equipment - Core Equipment Registry
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Core identification
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    subcategory TEXT,
    location TEXT,

    -- Technical details
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    part_number TEXT,

    -- Status
    status TEXT DEFAULT 'operational' CHECK (status IN (
        'operational', 'degraded', 'failed', 'maintenance', 'decommissioned'
    )),
    is_critical BOOLEAN DEFAULT false,

    -- Installation info
    installed_at TIMESTAMPTZ,
    commissioned_at TIMESTAMPTZ,
    warranty_expires_at TIMESTAMPTZ,

    -- Documentation
    manual_reference TEXT,
    notes TEXT,
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

-- Indexes for pms_equipment
CREATE INDEX IF NOT EXISTS idx_pms_equipment_yacht ON public.pms_equipment(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_category ON public.pms_equipment(yacht_id, category);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_status ON public.pms_equipment(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_pms_equipment_critical ON public.pms_equipment(yacht_id) WHERE is_critical = true;

-- RLS for pms_equipment
ALTER TABLE public.pms_equipment ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht equipment"
    ON public.pms_equipment FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can manage their yacht equipment"
    ON public.pms_equipment FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

COMMENT ON TABLE public.pms_equipment IS 'Core equipment registry for yacht maintenance';


-- =============================================================================
-- 2. pms_work_orders - Work Order Management
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_work_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identification
    wo_number TEXT,
    title TEXT NOT NULL,
    description TEXT,

    -- Type and priority
    wo_type TEXT DEFAULT 'corrective' CHECK (wo_type IN (
        'corrective', 'preventive', 'predictive', 'emergency', 'project'
    )),
    priority TEXT DEFAULT 'medium' CHECK (priority IN (
        'low', 'medium', 'high', 'critical'
    )),

    -- Status
    status TEXT DEFAULT 'open' CHECK (status IN (
        'draft', 'open', 'in_progress', 'on_hold', 'completed', 'cancelled'
    )),

    -- Associations
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    fault_id UUID,

    -- Assignment
    assigned_to UUID,
    assigned_at TIMESTAMPTZ,

    -- Scheduling
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    due_date TIMESTAMPTZ,

    -- Completion
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completed_by UUID,
    completion_notes TEXT,

    -- Cost tracking
    estimated_hours NUMERIC(6,2),
    actual_hours NUMERIC(6,2),
    estimated_cost NUMERIC(12,2),
    actual_cost NUMERIC(12,2),

    -- Vendor info (for email matching)
    vendor_id UUID,
    vendor_contact_hash TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

-- Indexes for pms_work_orders
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_yacht ON public.pms_work_orders(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_status ON public.pms_work_orders(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_equipment ON public.pms_work_orders(equipment_id);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_assigned ON public.pms_work_orders(assigned_to);
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_wo_number ON public.pms_work_orders(yacht_id, wo_number);

-- RLS for pms_work_orders
ALTER TABLE public.pms_work_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht work orders"
    ON public.pms_work_orders FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can manage their yacht work orders"
    ON public.pms_work_orders FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

COMMENT ON TABLE public.pms_work_orders IS 'Work order management for yacht maintenance';


-- =============================================================================
-- 3. pms_parts - Parts Inventory
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identification
    name TEXT NOT NULL,
    part_number TEXT,
    description TEXT,
    category TEXT,

    -- Inventory
    quantity_on_hand INTEGER DEFAULT 0,
    quantity_minimum INTEGER DEFAULT 0,
    quantity_reorder INTEGER DEFAULT 0,
    unit_of_measure TEXT DEFAULT 'each',

    -- Location
    storage_location TEXT,

    -- Pricing
    unit_cost NUMERIC(12,2),
    currency TEXT DEFAULT 'USD',

    -- Supplier info
    supplier_id UUID,
    supplier_part_number TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_parts_yacht ON public.pms_parts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_parts_part_number ON public.pms_parts(yacht_id, part_number);

ALTER TABLE public.pms_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht parts"
    ON public.pms_parts FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));


-- =============================================================================
-- 4. pms_faults - Fault/Defect Tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_faults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identification
    fault_number TEXT,
    title TEXT NOT NULL,
    description TEXT,

    -- Classification
    severity TEXT DEFAULT 'minor' CHECK (severity IN (
        'cosmetic', 'minor', 'major', 'critical', 'safety'
    )),
    category TEXT,

    -- Status
    status TEXT DEFAULT 'open' CHECK (status IN (
        'open', 'investigating', 'work_ordered', 'resolved', 'closed', 'deferred'
    )),

    -- Associations
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,

    -- Reporting
    reported_by UUID,
    reported_at TIMESTAMPTZ DEFAULT NOW(),

    -- Resolution
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,
    resolution_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_faults_yacht ON public.pms_faults(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_faults_status ON public.pms_faults(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_pms_faults_equipment ON public.pms_faults(equipment_id);

ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht faults"
    ON public.pms_faults FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));


-- =============================================================================
-- 5. pms_purchase_orders - Purchase Order Tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identification
    po_number TEXT,
    title TEXT,

    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft', 'pending', 'approved', 'ordered', 'partial', 'received', 'cancelled'
    )),

    -- Supplier
    supplier_id UUID,
    supplier_name TEXT,

    -- Amounts
    subtotal NUMERIC(12,2),
    tax NUMERIC(12,2),
    total NUMERIC(12,2),
    currency TEXT DEFAULT 'USD',

    -- Dates
    ordered_at TIMESTAMPTZ,
    expected_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_purchase_orders_yacht ON public.pms_purchase_orders(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_purchase_orders_status ON public.pms_purchase_orders(yacht_id, status);

ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht purchase orders"
    ON public.pms_purchase_orders FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));


-- =============================================================================
-- 6. pms_suppliers - Supplier/Vendor Registry
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pms_suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Basic info
    name TEXT NOT NULL,
    category TEXT,

    -- Contact
    email TEXT,
    email_hash TEXT,
    phone TEXT,
    website TEXT,

    -- Address
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT,

    -- Domain for email matching
    domain TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    notes TEXT,

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_suppliers_yacht ON public.pms_suppliers(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_suppliers_email_hash ON public.pms_suppliers(email_hash);
CREATE INDEX IF NOT EXISTS idx_pms_suppliers_domain ON public.pms_suppliers(domain);

ALTER TABLE public.pms_suppliers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht suppliers"
    ON public.pms_suppliers FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));


RAISE NOTICE 'Migration 000: Created core PMS tables successfully';
