-- ============================================================================
-- INVENTORY TABLES
-- ============================================================================
-- Supports: /v1/inventory/* endpoints

-- PARTS TABLE (Master list of parts/spares)
CREATE TABLE IF NOT EXISTS public.parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identification
    name TEXT NOT NULL,
    part_number TEXT,
    manufacturer TEXT,
    description TEXT,

    -- Classification
    category TEXT,                           -- 'filter', 'gasket', 'belt', 'sensor', 'pump', etc.
    model_compatibility JSONB DEFAULT '[]'::jsonb,  -- ['CAT3516', 'MTU4000']

    -- Pricing (for ordering)
    unit_price NUMERIC(12,2),
    currency TEXT DEFAULT 'USD',

    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'discontinued', 'superseded')),
    superseded_by UUID REFERENCES public.parts(id),

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.parts IS 'Master list of parts/spares that can be stocked';
COMMENT ON COLUMN public.parts.model_compatibility IS 'Equipment models this part is compatible with';

-- STOCK LOCATIONS TABLE
CREATE TABLE IF NOT EXISTS public.stock_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Location info
    name TEXT NOT NULL,                      -- "Engine Room Locker A"
    description TEXT,
    deck TEXT,
    position TEXT,                           -- Shelf/bin labels

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.stock_locations IS 'Physical storage locations on the yacht';

-- STOCK LEVELS TABLE
CREATE TABLE IF NOT EXISTS public.stock_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.parts(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES public.stock_locations(id) ON DELETE CASCADE,

    -- Quantities
    quantity INTEGER NOT NULL DEFAULT 0,
    min_quantity INTEGER DEFAULT 0,
    max_quantity INTEGER,
    reorder_quantity INTEGER,

    -- Tracking
    last_counted_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT unique_part_location UNIQUE (part_id, location_id)
);

COMMENT ON TABLE public.stock_levels IS 'Current inventory levels per part per location';

-- SUPPLIERS TABLE
CREATE TABLE IF NOT EXISTS public.suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Info
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address JSONB,                           -- {street, city, country, postal_code}

    -- Classification
    supplier_type TEXT,                      -- 'oem', 'distributor', 'service', 'general'
    is_preferred BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.suppliers IS 'Vendors and OEMs for parts ordering';

-- PURCHASE ORDERS TABLE
CREATE TABLE IF NOT EXISTS public.purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,

    -- PO info
    po_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'confirmed', 'partially_received', 'received', 'closed', 'cancelled')),

    -- Dates
    ordered_at TIMESTAMPTZ,
    expected_at DATE,
    received_at TIMESTAMPTZ,

    -- Financials
    currency TEXT DEFAULT 'USD',
    total_amount NUMERIC(12,2),
    tax_amount NUMERIC(12,2),

    -- Author
    created_by UUID,                         -- References auth.users(id)

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.purchase_orders IS 'Purchase orders for parts/supplies';

-- PURCHASE ORDER LINES TABLE
CREATE TABLE IF NOT EXISTS public.purchase_order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    purchase_order_id UUID NOT NULL REFERENCES public.purchase_orders(id) ON DELETE CASCADE,
    part_id UUID REFERENCES public.parts(id) ON DELETE SET NULL,

    -- Line item details
    description TEXT,
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.purchase_order_lines IS 'Individual line items on purchase orders';

-- Indexes for parts
CREATE INDEX IF NOT EXISTS idx_parts_yacht_id ON public.parts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_parts_part_number ON public.parts(yacht_id, part_number);
CREATE INDEX IF NOT EXISTS idx_parts_manufacturer ON public.parts(yacht_id, manufacturer);
CREATE INDEX IF NOT EXISTS idx_parts_category ON public.parts(yacht_id, category);
CREATE INDEX IF NOT EXISTS idx_parts_name_gin ON public.parts USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_parts_description_gin ON public.parts USING gin (description gin_trgm_ops);

-- Indexes for stock_locations
CREATE INDEX IF NOT EXISTS idx_stock_locations_yacht_id ON public.stock_locations(yacht_id);

-- Indexes for stock_levels
CREATE INDEX IF NOT EXISTS idx_stock_levels_yacht_id ON public.stock_levels(yacht_id);
CREATE INDEX IF NOT EXISTS idx_stock_levels_part_id ON public.stock_levels(part_id, yacht_id);
CREATE INDEX IF NOT EXISTS idx_stock_levels_location_id ON public.stock_levels(location_id);
CREATE INDEX IF NOT EXISTS idx_stock_levels_low_stock ON public.stock_levels(yacht_id) WHERE quantity <= min_quantity;

-- Indexes for suppliers
CREATE INDEX IF NOT EXISTS idx_suppliers_yacht_id ON public.suppliers(yacht_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_preferred ON public.suppliers(yacht_id) WHERE is_preferred = true;

-- Indexes for purchase_orders
CREATE INDEX IF NOT EXISTS idx_purchase_orders_yacht_id ON public.purchase_orders(yacht_id);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON public.purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON public.purchase_orders(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_po_number ON public.purchase_orders(yacht_id, po_number);

-- Indexes for purchase_order_lines
CREATE INDEX IF NOT EXISTS idx_po_lines_yacht_id ON public.purchase_order_lines(yacht_id);
CREATE INDEX IF NOT EXISTS idx_po_lines_po_id ON public.purchase_order_lines(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_po_lines_part_id ON public.purchase_order_lines(part_id);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 025 Complete - Created inventory tables (parts, stock_locations, stock_levels, suppliers, purchase_orders, purchase_order_lines)';
END $$;
