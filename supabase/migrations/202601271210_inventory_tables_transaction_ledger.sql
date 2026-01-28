-- Migration: 20260127_210_inventory_tables_transaction_ledger.sql
-- Purpose: Create append-only inventory transaction ledger for Part Lens v2
-- Date: 2026-01-27
-- Doctrine: Stock derived from transactions, not mutable columns

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- Per Part Lens v2 doctrine:
-- - on_hand MUST be derived from append-only pms_inventory_transactions
-- - No direct writes to pms_parts.quantity_on_hand allowed
-- - Idempotency enforced by DB unique constraint (yacht_id, idempotency_key)
-- - All stock changes recorded as transactions; view computes on_hand
-- ============================================================================

-- ============================================================================
-- 1. pms_inventory_stock - Stock location records (links parts to locations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_inventory_stock (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    location TEXT NOT NULL DEFAULT 'default',
    -- quantity is DERIVED from transactions, but cached for performance
    -- IMPORTANT: This column is ONLY updated by triggers, never by handlers
    quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one stock record per part per location per yacht
    UNIQUE(yacht_id, part_id, location)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pms_inventory_stock_yacht_id
    ON public.pms_inventory_stock(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_inventory_stock_part_id
    ON public.pms_inventory_stock(yacht_id, part_id);
CREATE INDEX IF NOT EXISTS idx_pms_inventory_stock_location
    ON public.pms_inventory_stock(yacht_id, location);

-- RLS
ALTER TABLE public.pms_inventory_stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_inventory_stock FORCE ROW LEVEL SECURITY;

-- RLS Policies
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_stock' AND policyname = 'crew_select_own_yacht_stock') THEN
        CREATE POLICY "crew_select_own_yacht_stock" ON public.pms_inventory_stock
            FOR SELECT TO authenticated
            USING (yacht_id = public.get_user_yacht_id());
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_stock' AND policyname = 'crew_insert_stock') THEN
        CREATE POLICY "crew_insert_stock" ON public.pms_inventory_stock
            FOR INSERT TO authenticated
            WITH CHECK (
                yacht_id = public.get_user_yacht_id()
                AND public.get_user_role() = ANY (ARRAY['deckhand', 'bosun', 'eto', 'chief_engineer', 'captain', 'manager', 'purser']::text[])
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_stock' AND policyname = 'service_role_full_access_stock') THEN
        CREATE POLICY "service_role_full_access_stock" ON public.pms_inventory_stock
            FOR ALL TO service_role
            USING (true) WITH CHECK (true);
    END IF;
END $$;

COMMENT ON TABLE public.pms_inventory_stock IS 'Stock location records linking parts to locations. quantity is cache updated by trigger.';

-- ============================================================================
-- 2. pms_inventory_transactions - Append-only transaction ledger
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES public.pms_inventory_stock(id) ON DELETE CASCADE,

    -- Transaction details
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'received',         -- Parts received from supplier
        'consumed',         -- Parts consumed for work/maintenance
        'adjusted',         -- Manual stock adjustment (SIGNED action)
        'transferred_in',   -- Received from transfer
        'transferred_out',  -- Sent via transfer
        'write_off',        -- Written off (SIGNED action)
        'returned',         -- Returned to supplier
        'initial'           -- Initial stock count
    )),
    quantity_change INTEGER NOT NULL CHECK (quantity_change != 0),

    -- Context
    work_order_id UUID,                -- Link to work order if applicable
    supplier_id UUID,                  -- Link to supplier for receive/return
    reference_id UUID,                 -- Generic reference (transfer partner, etc.)

    -- Idempotency (DB-enforced)
    idempotency_key TEXT,              -- Unique per yacht for duplicate detection

    -- Additional data
    reason TEXT,                       -- Required for adjustments/write-offs
    notes TEXT,
    photo_storage_path TEXT,           -- Photo of received goods

    -- Audit
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CONSTRAINT: No duplicate idempotency keys per yacht
    CONSTRAINT uq_inventory_txn_idempotency UNIQUE (yacht_id, idempotency_key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pms_inventory_transactions_yacht
    ON public.pms_inventory_transactions(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_inventory_transactions_stock_id
    ON public.pms_inventory_transactions(stock_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pms_inventory_transactions_type
    ON public.pms_inventory_transactions(yacht_id, transaction_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pms_inventory_transactions_work_order
    ON public.pms_inventory_transactions(work_order_id) WHERE work_order_id IS NOT NULL;

-- Partial unique index for idempotency (only where key is provided)
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_txn_idempotency_partial
    ON public.pms_inventory_transactions(yacht_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- RLS
ALTER TABLE public.pms_inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_inventory_transactions FORCE ROW LEVEL SECURITY;

-- RLS Policies
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'crew_select_own_yacht_txn') THEN
        CREATE POLICY "crew_select_own_yacht_txn" ON public.pms_inventory_transactions
            FOR SELECT TO authenticated
            USING (yacht_id = public.get_user_yacht_id());
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'crew_insert_txn') THEN
        CREATE POLICY "crew_insert_txn" ON public.pms_inventory_transactions
            FOR INSERT TO authenticated
            WITH CHECK (
                yacht_id = public.get_user_yacht_id()
                AND public.get_user_role() = ANY (ARRAY['deckhand', 'bosun', 'eto', 'chief_engineer', 'captain', 'manager', 'purser']::text[])
            );
    END IF;

    -- DELETE policy: Only manager can delete transactions (rare corrections)
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'manager_delete_txn') THEN
        CREATE POLICY "manager_delete_txn" ON public.pms_inventory_transactions
            FOR DELETE TO authenticated
            USING (
                yacht_id = public.get_user_yacht_id()
                AND public.get_user_role() = 'manager'
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'service_role_full_access_txn') THEN
        CREATE POLICY "service_role_full_access_txn" ON public.pms_inventory_transactions
            FOR ALL TO service_role
            USING (true) WITH CHECK (true);
    END IF;
END $$;

COMMENT ON TABLE public.pms_inventory_transactions IS
    'Append-only transaction ledger. Stock derived from SUM(quantity_change). Idempotency via unique(yacht_id, idempotency_key).';

-- ============================================================================
-- 3. Trigger: Auto-update pms_inventory_stock.quantity on transaction insert
-- ============================================================================
CREATE OR REPLACE FUNCTION public.update_inventory_stock_quantity()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the cached quantity in pms_inventory_stock
    UPDATE public.pms_inventory_stock
    SET
        quantity = quantity + NEW.quantity_change,
        updated_at = NOW()
    WHERE id = NEW.stock_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_stock_on_transaction ON public.pms_inventory_transactions;

CREATE TRIGGER trg_update_stock_on_transaction
    AFTER INSERT ON public.pms_inventory_transactions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_inventory_stock_quantity();

COMMENT ON TRIGGER trg_update_stock_on_transaction ON public.pms_inventory_transactions IS
    'Auto-updates pms_inventory_stock.quantity cache when transactions are inserted.';

-- ============================================================================
-- 4. Helper function: Get or create stock record for a part/location
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_or_create_stock_id(
    p_yacht_id UUID,
    p_part_id UUID,
    p_location TEXT DEFAULT 'default'
)
RETURNS UUID AS $$
DECLARE
    v_stock_id UUID;
BEGIN
    -- Try to find existing stock record
    SELECT id INTO v_stock_id
    FROM public.pms_inventory_stock
    WHERE yacht_id = p_yacht_id
      AND part_id = p_part_id
      AND location = COALESCE(p_location, 'default');

    -- Create if not exists
    IF v_stock_id IS NULL THEN
        INSERT INTO public.pms_inventory_stock (yacht_id, part_id, location, quantity)
        VALUES (p_yacht_id, p_part_id, COALESCE(p_location, 'default'), 0)
        RETURNING id INTO v_stock_id;
    END IF;

    RETURN v_stock_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.get_or_create_stock_id IS
    'Returns stock_id for a part/location, creating the record if needed.';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT * FROM pms_inventory_stock WHERE yacht_id = 'your-yacht-id' LIMIT 5;
-- SELECT * FROM pms_inventory_transactions WHERE yacht_id = 'your-yacht-id' ORDER BY created_at DESC LIMIT 10;
-- SELECT SUM(quantity_change) FROM pms_inventory_transactions WHERE stock_id = 'stock-id';
