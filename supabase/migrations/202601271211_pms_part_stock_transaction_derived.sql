-- Migration: 20260127_211_pms_part_stock_transaction_derived.sql
-- Purpose: Replace pms_part_stock view to derive on_hand from transactions
-- Date: 2026-01-27
-- Doctrine: Stock MUST be derived from append-only transactions, not mutable columns
-- Defensive: Only runs if required tables exist

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- Per Part Lens v2 doctrine:
-- - pms_part_stock.on_hand MUST equal SUM of pms_inventory_transactions
-- - NO dependency on pms_parts.quantity_on_hand (mutable column)
-- - This view is the CANONICAL source of truth for stock levels
-- ============================================================================

DO $$
DECLARE
    has_inventory_stock BOOLEAN;
    has_inventory_transactions BOOLEAN;
    has_min_level BOOLEAN;
    has_reorder_multiple BOOLEAN;
    has_location BOOLEAN;
    has_is_critical BOOLEAN;
    has_department BOOLEAN;
    has_category BOOLEAN;
    has_name BOOLEAN;
    has_part_number BOOLEAN;
    view_sql TEXT;
BEGIN
    -- Check required tables
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') INTO has_inventory_stock;
    IF NOT has_inventory_stock THEN
        RAISE NOTICE 'pms_parts table does not exist - skipping transaction-derived views';
        RETURN;
    END IF;

    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_stock' AND table_schema = 'public') INTO has_inventory_stock;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') INTO has_inventory_transactions;

    IF NOT has_inventory_stock THEN
        RAISE NOTICE 'pms_inventory_stock table does not exist - skipping transaction-derived stock view';
        RETURN;
    END IF;

    -- Check which columns exist on pms_parts
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'min_level') INTO has_min_level;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'reorder_multiple') INTO has_reorder_multiple;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'location') INTO has_location;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'is_critical') INTO has_is_critical;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'department') INTO has_department;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'category') INTO has_category;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'name') INTO has_name;
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'part_number') INTO has_part_number;

    -- Drop existing view
    DROP VIEW IF EXISTS public.pms_part_stock CASCADE;

    -- Build pms_part_stock view dynamically
    view_sql := 'CREATE VIEW public.pms_part_stock AS SELECT p.yacht_id, p.id AS part_id, COALESCE(s.quantity, 0) AS on_hand';

    -- min_level
    IF has_min_level THEN
        view_sql := view_sql || ', COALESCE(p.min_level, 0) AS min_level';
    ELSE
        view_sql := view_sql || ', 0 AS min_level';
    END IF;

    -- reorder_multiple
    IF has_reorder_multiple THEN
        view_sql := view_sql || ', COALESCE(p.reorder_multiple, 1) AS reorder_multiple';
    ELSE
        view_sql := view_sql || ', 1 AS reorder_multiple';
    END IF;

    -- location
    IF has_location THEN
        view_sql := view_sql || ', COALESCE(s.location, p.location, ''default'') AS location';
    ELSE
        view_sql := view_sql || ', COALESCE(s.location, ''default'') AS location';
    END IF;

    -- is_critical
    IF has_is_critical THEN
        view_sql := view_sql || ', COALESCE(p.is_critical, false) AS is_critical';
    ELSE
        view_sql := view_sql || ', false AS is_critical';
    END IF;

    -- department
    IF has_department THEN
        view_sql := view_sql || ', p.department';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS department';
    END IF;

    -- category
    IF has_category THEN
        view_sql := view_sql || ', p.category';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS category';
    END IF;

    -- part_name
    IF has_name THEN
        view_sql := view_sql || ', p.name AS part_name';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS part_name';
    END IF;

    -- part_number
    IF has_part_number THEN
        view_sql := view_sql || ', p.part_number';
    ELSE
        view_sql := view_sql || ', NULL::TEXT AS part_number';
    END IF;

    -- stock_id
    view_sql := view_sql || ', s.id AS stock_id';

    -- FROM clause with JOIN
    view_sql := view_sql || ' FROM public.pms_parts p LEFT JOIN public.pms_inventory_stock s ON p.id = s.part_id AND p.yacht_id = s.yacht_id';

    EXECUTE view_sql;
    EXECUTE 'GRANT SELECT ON public.pms_part_stock TO authenticated';
    EXECUTE 'GRANT SELECT ON public.pms_part_stock TO service_role';

    RAISE NOTICE 'SUCCESS: pms_part_stock transaction-derived view created';

    -- v_stock_from_transactions (requires pms_inventory_transactions)
    IF has_inventory_transactions THEN
        DROP VIEW IF EXISTS public.v_stock_from_transactions CASCADE;

        EXECUTE '
            CREATE VIEW public.v_stock_from_transactions AS
            SELECT
                s.yacht_id,
                s.part_id,
                s.location,
                s.id AS stock_id,
                COALESCE(SUM(t.quantity_change), 0) AS derived_on_hand,
                s.quantity AS cached_quantity,
                CASE
                    WHEN s.quantity = COALESCE(SUM(t.quantity_change), 0) THEN ''OK''
                    ELSE ''DRIFT''
                END AS reconciliation_status,
                COUNT(t.id) AS transaction_count,
                MIN(t.created_at) AS first_transaction,
                MAX(t.created_at) AS last_transaction
            FROM public.pms_inventory_stock s
            LEFT JOIN public.pms_inventory_transactions t ON s.id = t.stock_id
            GROUP BY s.yacht_id, s.part_id, s.location, s.id, s.quantity
        ';
        EXECUTE 'GRANT SELECT ON public.v_stock_from_transactions TO authenticated';
        EXECUTE 'GRANT SELECT ON public.v_stock_from_transactions TO service_role';
        RAISE NOTICE 'SUCCESS: v_stock_from_transactions view created';
    ELSE
        RAISE NOTICE 'pms_inventory_transactions does not exist - skipping v_stock_from_transactions';
    END IF;

    -- v_low_stock_report (depends on pms_part_stock which we just created)
    DROP VIEW IF EXISTS public.v_low_stock_report CASCADE;

    EXECUTE '
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
            CASE WHEN ps.on_hand = 0 THEN true ELSE false END AS is_out_of_stock,
            CASE WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN true ELSE false END AS is_low_stock,
            CASE
                WHEN ps.min_level > 0 AND ps.on_hand < ps.min_level THEN
                    CEIL(GREATEST(ps.min_level - ps.on_hand, 1)::numeric / GREATEST(ps.reorder_multiple, 1)) * GREATEST(ps.reorder_multiple, 1)
                ELSE 0
            END::INTEGER AS suggested_order_qty,
            CASE
                WHEN ps.on_hand = 0 THEN ''critical''
                WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level * 0.5 THEN ''high''
                WHEN ps.min_level > 0 AND ps.on_hand <= ps.min_level THEN ''medium''
                ELSE ''low''
            END AS urgency
        FROM public.pms_part_stock ps
        WHERE ps.on_hand = 0
           OR (ps.min_level > 0 AND ps.on_hand <= ps.min_level)
        ORDER BY
            ps.is_critical DESC NULLS LAST,
            ps.on_hand = 0 DESC,
            ps.on_hand ASC
    ';
    EXECUTE 'GRANT SELECT ON public.v_low_stock_report TO authenticated';
    EXECUTE 'GRANT SELECT ON public.v_low_stock_report TO service_role';
    RAISE NOTICE 'SUCCESS: v_low_stock_report view created';
END $$;
