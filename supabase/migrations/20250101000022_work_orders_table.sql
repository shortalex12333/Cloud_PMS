-- ============================================================================
-- WORK ORDERS & HISTORY TABLES
-- ============================================================================
-- Supports: /v1/work-orders/create, /v1/work-orders/add-note, /v1/work-orders/close

-- WORK ORDERS TABLE
CREATE TABLE IF NOT EXISTS public.work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,

    -- Core fields
    title TEXT NOT NULL,
    description TEXT,

    -- Classification
    type TEXT NOT NULL DEFAULT 'corrective' CHECK (type IN ('scheduled', 'corrective', 'unplanned', 'inspection')),
    priority TEXT NOT NULL DEFAULT 'routine' CHECK (priority IN ('routine', 'important', 'critical', 'urgent')),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'in_progress', 'completed', 'deferred', 'cancelled')),

    -- Scheduling
    due_date DATE,
    due_hours INTEGER,                       -- For hour-based scheduling
    last_completed_date DATE,
    last_completed_hours INTEGER,
    frequency JSONB,                         -- {type:'hours'|'days'|'months', value:int}

    -- Assignment
    assigned_to UUID,                        -- References auth.users(id)
    created_by UUID,                         -- References auth.users(id)
    updated_by UUID,                         -- References auth.users(id)
    closed_by UUID,                          -- References auth.users(id)
    closed_at TIMESTAMPTZ,

    -- Related entities
    fault_id UUID,                           -- Link to originating fault if any

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.work_orders IS 'Planned and corrective maintenance work orders';
COMMENT ON COLUMN public.work_orders.frequency IS 'JSON schedule for recurring WOs: {type:"hours"|"days"|"months", value:number}';

-- WORK ORDER HISTORY TABLE
CREATE TABLE IF NOT EXISTS public.work_order_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    work_order_id UUID NOT NULL REFERENCES public.work_orders(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,

    -- Completion info
    completed_by UUID,                       -- References auth.users(id)
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status_on_completion TEXT DEFAULT 'completed' CHECK (status_on_completion IN ('completed', 'partial', 'failed', 'deferred')),

    -- Work details
    notes TEXT,
    hours_logged NUMERIC(5,2),

    -- Parts & Docs used
    parts_used JSONB DEFAULT '[]'::jsonb,    -- [{part_id, quantity, notes}]
    documents_used JSONB DEFAULT '[]'::jsonb, -- [{document_id, chunk_ids}]
    faults_related JSONB DEFAULT '[]'::jsonb, -- [{fault_id}]

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.work_order_history IS 'Historical record of work order completions for RAG and analytics';
COMMENT ON COLUMN public.work_order_history.notes IS 'Freeform notes - will be vectorized for RAG search';

-- Indexes for work_orders
CREATE INDEX IF NOT EXISTS idx_work_orders_yacht_id ON public.work_orders(yacht_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_equipment_id ON public.work_orders(equipment_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_status ON public.work_orders(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_work_orders_equipment_status ON public.work_orders(equipment_id, status, yacht_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_due_date ON public.work_orders(yacht_id, due_date) WHERE status IN ('planned', 'in_progress');
CREATE INDEX IF NOT EXISTS idx_work_orders_priority ON public.work_orders(yacht_id, priority) WHERE status NOT IN ('completed', 'cancelled');
CREATE INDEX IF NOT EXISTS idx_work_orders_title_gin ON public.work_orders USING gin (title gin_trgm_ops);

-- Indexes for work_order_history
CREATE INDEX IF NOT EXISTS idx_wo_history_yacht_id ON public.work_order_history(yacht_id);
CREATE INDEX IF NOT EXISTS idx_wo_history_work_order_id ON public.work_order_history(work_order_id);
CREATE INDEX IF NOT EXISTS idx_wo_history_equipment_id ON public.work_order_history(equipment_id);
CREATE INDEX IF NOT EXISTS idx_wo_history_completed_at ON public.work_order_history(yacht_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_wo_history_notes_gin ON public.work_order_history USING gin (notes gin_trgm_ops);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 022 Complete - Created work_orders and work_order_history tables';
END $$;
