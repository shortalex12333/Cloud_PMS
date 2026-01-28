-- ============================================================================
-- DEPLOYMENT-READY MIGRATION: Missing P0 Tables
-- ============================================================================
-- Date: 2026-01-22
-- Purpose: Create 4 missing P0 tables + add approval columns
-- Version: CORRECTED (RLS policies fixed for TENANT DB architecture)
--
-- Changes from Phase 3:
-- - RLS policies use service_role bypass instead of user_profiles lookup
-- - Simplified policies for TENANT DB (single yacht assumed)
-- - All FKs use pms_ prefix consistently
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PMS_WORK_ORDER_NOTES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_order_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'general' CHECK (note_type IN ('general', 'progress', 'issue', 'resolution')),
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_work_order_notes_work_order_id
    ON public.pms_work_order_notes(work_order_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pms_work_order_notes_created_by
    ON public.pms_work_order_notes(created_by);

COMMENT ON TABLE public.pms_work_order_notes IS
    'Notes/comments on work orders - REQUIRED for add_wo_note action';

-- Enable RLS
ALTER TABLE public.pms_work_order_notes ENABLE ROW LEVEL SECURITY;

-- RLS: Service role has full access (API uses service role)
CREATE POLICY "Service role full access"
    ON public.pms_work_order_notes FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS: Authenticated users can view (optional - for future direct user access)
CREATE POLICY "Authenticated users can view notes"
    ON public.pms_work_order_notes FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- 2. PMS_WORK_ORDER_PARTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_order_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    quantity_required INTEGER NOT NULL CHECK (quantity_required > 0),
    quantity_used INTEGER DEFAULT 0 CHECK (quantity_used >= 0),
    notes TEXT,
    added_by UUID NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    UNIQUE(work_order_id, part_id)
);

CREATE INDEX IF NOT EXISTS idx_pms_work_order_parts_work_order_id
    ON public.pms_work_order_parts(work_order_id);

CREATE INDEX IF NOT EXISTS idx_pms_work_order_parts_part_id
    ON public.pms_work_order_parts(part_id);

COMMENT ON TABLE public.pms_work_order_parts IS
    'Parts needed for work orders (shopping list) - REQUIRED for add_wo_part action';

-- Enable RLS
ALTER TABLE public.pms_work_order_parts ENABLE ROW LEVEL SECURITY;

-- RLS: Service role full access
CREATE POLICY "Service role full access"
    ON public.pms_work_order_parts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS: Authenticated users can view
CREATE POLICY "Authenticated users can view parts"
    ON public.pms_work_order_parts FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- 3. PMS_PART_USAGE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_part_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    transaction_type TEXT NOT NULL DEFAULT 'usage' CHECK (transaction_type IN (
        'usage', 'adjustment', 'restock', 'initial', 'transfer', 'waste', 'receiving'
    )),
    usage_reason TEXT CHECK (usage_reason IN (
        'work_order', 'maintenance', 'emergency', 'testing', 'other'
    )),
    notes TEXT,
    used_by UUID NOT NULL,
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_part_usage_yacht_id
    ON public.pms_part_usage(yacht_id);

CREATE INDEX IF NOT EXISTS idx_pms_part_usage_part_id
    ON public.pms_part_usage(part_id, used_at DESC);

CREATE INDEX IF NOT EXISTS idx_pms_part_usage_work_order_id
    ON public.pms_part_usage(work_order_id);

CREATE INDEX IF NOT EXISTS idx_pms_part_usage_equipment_id
    ON public.pms_part_usage(equipment_id);

CREATE INDEX IF NOT EXISTS idx_pms_part_usage_used_at
    ON public.pms_part_usage(used_at DESC);

COMMENT ON TABLE public.pms_part_usage IS
    'Inventory usage log (deduction events) - REQUIRED for complete_work_order and log_part_usage';

-- Enable RLS
ALTER TABLE public.pms_part_usage ENABLE ROW LEVEL SECURITY;

-- RLS: Service role full access
CREATE POLICY "Service role full access"
    ON public.pms_part_usage FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS: Authenticated users can view
CREATE POLICY "Authenticated users can view usage"
    ON public.pms_part_usage FOR SELECT
    TO authenticated
    USING (true);

-- ----------------------------------------------------------------------------
-- 4. SHOPPING_LIST_ITEMS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.shopping_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    quantity_requested INTEGER NOT NULL DEFAULT 1 CHECK (quantity_requested > 0),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    notes TEXT,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'ordered', 'cancelled')),
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_shopping_list_items_yacht_status
    ON public.shopping_list_items(yacht_id, status)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_shopping_list_items_part
    ON public.shopping_list_items(part_id);

COMMENT ON TABLE public.shopping_list_items IS
    'Shopping list for parts to order - feed into purchase orders';

-- Enable RLS
ALTER TABLE public.shopping_list_items ENABLE ROW LEVEL SECURITY;

-- RLS: Service role full access
CREATE POLICY "Service role full access"
    ON public.shopping_list_items FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS: Authenticated users can view non-deleted items
CREATE POLICY "Authenticated users can view shopping list"
    ON public.shopping_list_items FOR SELECT
    TO authenticated
    USING (deleted_at IS NULL);

-- ----------------------------------------------------------------------------
-- 5. ADD APPROVAL COLUMNS TO PMS_PURCHASE_ORDERS
-- ----------------------------------------------------------------------------
ALTER TABLE public.pms_purchase_orders
ADD COLUMN IF NOT EXISTS approved_by UUID,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS approval_notes TEXT,
ADD COLUMN IF NOT EXISTS received_by UUID,
ADD COLUMN IF NOT EXISTS receiving_notes TEXT,
ADD COLUMN IF NOT EXISTS ordered_by UUID;

COMMENT ON COLUMN public.pms_purchase_orders.approved_by IS
    'User ID who approved the purchase order (HOD)';

COMMENT ON COLUMN public.pms_purchase_orders.approved_at IS
    'Timestamp when PO was approved';

COMMENT ON COLUMN public.pms_purchase_orders.ordered_by IS
    'User ID who placed the order with supplier';

COMMENT ON COLUMN public.pms_purchase_orders.received_by IS
    'User ID who committed the receiving (or logged delivery)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Run this to verify deployment:
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage', 'shopping_list_items')
-- ORDER BY table_name, ordinal_position;
-- ============================================================================
