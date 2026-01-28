-- Migration: 20260127_212_pms_part_stock_canonical_from_transactions.sql
-- Purpose: pms_part_stock.on_hand derived DIRECTLY from transactions (not cache)
-- Date: 2026-01-27
-- Doctrine: on_hand = SUM(pms_inventory_transactions.quantity_change)

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- CRITICAL FIX: Previous migration used pms_inventory_stock.quantity (cache).
-- Doctrine requires on_hand to be computed from append-only transactions.
--
-- pms_inventory_stock.quantity is NOW non-authoritative (optional cache).
-- The CANONICAL source of truth is SUM(transactions).
-- ============================================================================

DO $$
DECLARE
    has_parts BOOLEAN;
    has_inventory_stock BOOLEAN;
    has_inventory_transactions BOOLEAN;
BEGIN
    -- Check required tables exist
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') INTO has_parts;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_stock' AND table_schema = 'public') INTO has_inventory_stock;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') INTO has_inventory_transactions;

    IF NOT has_parts THEN
        RAISE NOTICE 'pms_parts not found - skipping migration';
        RETURN;
    END IF;

    IF NOT has_inventory_stock OR NOT has_inventory_transactions THEN
        RAISE NOTICE 'Inventory tables not found - skipping canonical view';
        RETURN;
    END IF;

    -- Drop existing views (order matters due to dependencies)
    DROP VIEW IF EXISTS public.v_low_stock_report CASCADE;
    DROP VIEW IF EXISTS public.pms_part_stock CASCADE;
    DROP VIEW IF EXISTS public.v_stock_from_transactions CASCADE;

    -- ========================================================================
    -- v_stock_from_transactions: Compute on_hand from SUM(transactions)
    -- ========================================================================
    CREATE VIEW public.v_stock_from_transactions AS
    SELECT
        s.yacht_id,
        s.part_id,
        s.location,
        s.id AS stock_id,
        -- CANONICAL: on_hand derived from transaction sum
        COALESCE(SUM(t.quantity_change), 0)::INTEGER AS on_hand,
        -- Cache comparison (for reconciliation)
        s.quantity AS cached_quantity,
        -- Drift detection
        CASE
            WHEN s.quantity = COALESCE(SUM(t.quantity_change), 0) THEN 'OK'
            ELSE 'DRIFT'
        END AS reconciliation_status,
        COUNT(t.id) AS transaction_count,
        MIN(t.created_at) AS first_transaction,
        MAX(t.created_at) AS last_transaction
    FROM public.pms_inventory_stock s
    LEFT JOIN public.pms_inventory_transactions t ON s.id = t.stock_id
    GROUP BY s.yacht_id, s.part_id, s.location, s.id, s.quantity;

    GRANT SELECT ON public.v_stock_from_transactions TO authenticated;
    GRANT SELECT ON public.v_stock_from_transactions TO service_role;

    RAISE NOTICE 'SUCCESS: v_stock_from_transactions created (SUM-based)';

    -- ========================================================================
    -- pms_part_stock: CANONICAL view - on_hand from v_stock_from_transactions
    -- ========================================================================
    -- This is the ONLY authoritative source for stock levels.
    -- Handlers and suggestions MUST read from this view.
    CREATE VIEW public.pms_part_stock AS
    SELECT
        p.yacht_id,
        p.id AS part_id,
        -- on_hand from transaction sum (NOT from cache)
        COALESCE(v.on_hand, 0) AS on_hand,
        -- Part metadata
        COALESCE(p.min_level, 0) AS min_level,
        COALESCE(p.reorder_multiple, 1) AS reorder_multiple,
        COALESCE(v.location, p.location, 'default') AS location,
        COALESCE(p.is_critical, false) AS is_critical,
        p.department,
        p.category,
        p.name AS part_name,
        p.part_number,
        -- Stock record ID (needed for transaction inserts)
        v.stock_id
    FROM public.pms_parts p
    LEFT JOIN public.v_stock_from_transactions v
        ON p.id = v.part_id
        AND p.yacht_id = v.yacht_id;

    GRANT SELECT ON public.pms_part_stock TO authenticated;
    GRANT SELECT ON public.pms_part_stock TO service_role;

    RAISE NOTICE 'SUCCESS: pms_part_stock created (canonical, from v_stock_from_transactions)';

    -- ========================================================================
    -- v_low_stock_report: Uses canonical pms_part_stock
    -- ========================================================================
    CREATE VIEW public.v_low_stock_report AS
    SELECT
        ps.part_id,
        ps.yacht_id,
        ps.part_name,
        ps.part_number,
        ps.is_critical,
        ps.on_hand,
        ps.min_level,
        ps.reorder_multiple,
        ps.location,
        ps.category,
        ps.department,
        -- Derived flags
        CASE WHEN ps.on_hand = 0 THEN true ELSE false END AS is_out_of_stock,
        CASE WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN true ELSE false END AS is_low_stock,
        -- Suggested order qty: round_up(max(min_level - on_hand, 1), reorder_multiple)
        CASE
            WHEN ps.min_level > 0 AND ps.on_hand < ps.min_level THEN
                CEIL(GREATEST(ps.min_level - ps.on_hand, 1)::numeric / GREATEST(ps.reorder_multiple, 1)) * GREATEST(ps.reorder_multiple, 1)
            ELSE 0
        END::INTEGER AS suggested_order_qty,
        -- Urgency
        CASE
            WHEN ps.on_hand = 0 THEN 'critical'
            WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level * 0.5 THEN 'high'
            WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN 'medium'
            ELSE 'low'
        END AS urgency
    FROM public.pms_part_stock ps
    WHERE ps.on_hand = 0
       OR (ps.min_level > 0 AND ps.on_hand <= ps.min_level)
    ORDER BY
        ps.is_critical DESC NULLS LAST,
        ps.on_hand = 0 DESC,
        ps.on_hand ASC;

    GRANT SELECT ON public.v_low_stock_report TO authenticated;
    GRANT SELECT ON public.v_low_stock_report TO service_role;

    RAISE NOTICE 'SUCCESS: v_low_stock_report created';

    -- ========================================================================
    -- Add comment marking pms_inventory_stock.quantity as NON-AUTHORITATIVE
    -- ========================================================================
    COMMENT ON COLUMN public.pms_inventory_stock.quantity IS
        'NON-AUTHORITATIVE CACHE. Updated by trigger for performance. '
        'CANONICAL on_hand is SUM(pms_inventory_transactions.quantity_change). '
        'Use v_stock_from_transactions for reconciliation.';

END $$;

-- ============================================================================
-- VERIFICATION QUERIES (run these to verify)
-- ============================================================================
-- 1. Verify on_hand equals transaction sum:
-- SELECT part_id, on_hand, (SELECT SUM(quantity_change) FROM pms_inventory_transactions t
--    JOIN pms_inventory_stock s ON t.stock_id = s.id WHERE s.part_id = ps.part_id)
-- FROM pms_part_stock ps WHERE yacht_id = 'your-yacht' LIMIT 10;

-- 2. Check for drift between cache and transactions:
-- SELECT * FROM v_stock_from_transactions WHERE reconciliation_status = 'DRIFT';

-- 3. Verify pms_part_stock reads from v_stock_from_transactions (not cache):
-- EXPLAIN ANALYZE SELECT * FROM pms_part_stock WHERE yacht_id = 'your-yacht';
